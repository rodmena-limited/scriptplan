from typing import TYPE_CHECKING, Optional

from scriptplan.core.property import PropertyTreeNode

if TYPE_CHECKING:
    from scriptplan.core.project import Project


class Scenario(PropertyTreeNode):
    def __init__(self, project: "Project", id: str, name: str, parent: Optional["Scenario"]) -> None:
        super().__init__(project.scenarios, id, name, parent)
