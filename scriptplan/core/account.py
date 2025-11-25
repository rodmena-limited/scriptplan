"""Account module implementing financial transaction records.

An Account is an object to record financial transactions. Alternatively, an
Account can just be a container for a set of Accounts. In this case it
cannot directly record any transactions.
"""

from typing import TYPE_CHECKING, Any, Optional

from scriptplan.core.property import PropertyTreeNode
from scriptplan.core.scenario_data import ScenarioData

if TYPE_CHECKING:
    from scriptplan.core.project import Project


class AccountScenario(ScenarioData):
    """Handles the scenario-specific features of an Account object."""

    def __init__(self, account: "Account", scenarioIdx: int, attributes: dict[str, Any]) -> None:
        super().__init__(account, scenarioIdx, attributes)
        self._credits: list[Any] = []

    def _get(self, attrName: str) -> Any:
        """Get attribute value using property's attribute access."""
        return self.property.get(attrName, self.scenarioIdx)

    def query_balance(self, query: Any) -> None:
        """Query the account balance.

        The balance is the turnover from project start to the start of the query period.
        """
        startIdx = 0
        endIdx = self.project.dateToIdx(query.start) if hasattr(self.project, "dateToIdx") else 0

        amount = self.turnover(startIdx, endIdx)
        query.sortable = amount
        query.numerical = amount
        if hasattr(query, "currencyFormat") and query.currencyFormat:
            query.string = query.currencyFormat.format(amount)
        else:
            query.string = str(amount)

    def query_turnover(self, query: Any) -> None:
        """Query the turnover for a period."""
        startIdx = self.project.dateToIdx(query.start) if hasattr(self.project, "dateToIdx") else 0
        endIdx = self.project.dateToIdx(query.end) if hasattr(self.project, "dateToIdx") else 0

        amount = self.turnover(startIdx, endIdx)
        query.sortable = amount
        query.numerical = amount
        if hasattr(query, "currencyFormat") and query.currencyFormat:
            query.string = query.currencyFormat.format(amount)
        else:
            query.string = str(amount)

    def turnover(self, startIdx: int, endIdx: int) -> float:
        """Compute the turnover for the period between startIdx and endIdx."""
        amount = 0.0

        # Accumulate amounts directly credited to the account during the interval
        credits = self._get("credits")
        if credits:
            startDate = self.project.idxToDate(startIdx) if hasattr(self.project, "idxToDate") else None
            endDate = self.project.idxToDate(endIdx) if hasattr(self.project, "idxToDate") else None

            if startDate and endDate:
                for credit in credits:
                    if hasattr(credit, "date") and hasattr(credit, "amount") and startDate <= credit.date < endDate:
                        amount += credit.amount

        # Note: PropertyTreeNode doesn't have container() method by default, using hasattr check
        if hasattr(self.property, "container") and self.property.container():
            if not self.property.adoptees:
                # Normal case: accumulate turnover of child accounts
                for child in self.property.children:
                    child_scenario = child.scenario(self.scenarioIdx)  # type: ignore[attr-defined]
                    if child_scenario:
                        amount += child_scenario.turnover(startIdx, endIdx)
            else:
                # Special case for meta account (balance calculation)
                # First adoptee is cost account, second is revenue account
                if len(self.property.adoptees) >= 2:
                    adoptee0_scenario = self.property.adoptees[0].scenario(self.scenarioIdx)  # type: ignore[attr-defined]
                    adoptee1_scenario = self.property.adoptees[1].scenario(self.scenarioIdx)  # type: ignore[attr-defined]
                    if adoptee0_scenario and adoptee1_scenario:
                        amount += -adoptee0_scenario.turnover(startIdx, endIdx) + adoptee1_scenario.turnover(
                            startIdx, endIdx
                        )
        else:
            aggregate = self.property.get("aggregate")
            if aggregate == "tasks" or aggregate == ":tasks":
                for task in self.project.tasks:
                    task_scenario = task.scenario(self.scenarioIdx)  # type: ignore[attr-defined]
                    if task_scenario and hasattr(task_scenario, "turnover"):
                        amount += task_scenario.turnover(startIdx, endIdx, self.property, None, False)
            elif aggregate == "resources" or aggregate == ":resources":
                for resource in self.project.resources:
                    if resource.leaf():
                        resource_scenario = resource.scenario(self.scenarioIdx)  # type: ignore[attr-defined]
                        if resource_scenario and hasattr(resource_scenario, "turnover"):
                            amount += resource_scenario.turnover(startIdx, endIdx, self.property, None, False)
        return amount


class Account(PropertyTreeNode):
    """An Account records financial transactions.

    An Account can also be a container for other Accounts, in which case
    it cannot directly record transactions but aggregates them from children.
    """

    def __init__(self, project: "Project", id: str, name: str, parent: Optional["Account"]) -> None:
        super().__init__(project.accounts, id, name, parent)
        project.addAccount(self)

        # Initialize scenario data array
        self.data: list[Optional[AccountScenario]] = [None] * project.scenarioCount()
        for i in range(project.scenarioCount()):
            AccountScenario(self, i, self._scenarioAttributes[i])

    def scenario(self, scenarioIdx: int) -> Optional[AccountScenario]:
        """Return a reference to the scenarioIdx-th scenario."""
        return self.data[scenarioIdx]

    def container(self) -> bool:
        """Return True if this account is a container (has children)."""
        return len(self.children) > 0 or len(self.adoptees) > 0

    def turnover(self, scenarioIdx: int, startIdx: int, endIdx: int) -> float:
        """Get the turnover for the specified scenario and period."""
        scenario = self.data[scenarioIdx]
        return scenario.turnover(startIdx, endIdx) if scenario else 0.0
