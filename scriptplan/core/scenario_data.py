from typing import TYPE_CHECKING, Any, Optional

from scriptplan.utils.message_handler import MessageHandler, SourceFileInfo

if TYPE_CHECKING:
    from scriptplan.core.project import Project
    from scriptplan.core.property import PropertyTreeNode


class ScenarioData:
    def __init__(self, property_node: "PropertyTreeNode", idx: int, attributes: dict[str, Any]) -> None:
        self.property = property_node
        self.project: Project = property_node.project
        self.scenarioIdx = idx
        self.attributes = attributes
        self.messageHandler = MessageHandler()  # Should be singleton in real app

        # Register the scenario with the property.
        if self.property.data is None:
            # Initialize if not present, assuming it's a list
            # In PropertyTreeNode we initialized it as list of None
            self.property.data = [None] * (
                self.project.scenarioCount() if hasattr(self.project, "scenarioCount") else 1
            )

        # Ensure list is big enough
        while len(self.property.data) <= idx:
            self.property.data.append(None)

        self.property.data[idx] = self

    def deep_clone(self) -> "ScenarioData":
        return self

    def a(self, attributeName: str) -> Any:
        return self.attributes[attributeName].get()

    def error(
        self,
        id: str,
        text: str,
        sourceFileInfo: Optional[SourceFileInfo] = None,
        property_node: Optional["PropertyTreeNode"] = None,
    ) -> None:
        # Delegating to message handler
        # Simplified context passing
        self.messageHandler.error(id, text, sourceFileInfo or self.property.sourceFileInfo)

    def warning(
        self,
        id: str,
        text: str,
        sourceFileInfo: Optional[SourceFileInfo] = None,
        property_node: Optional["PropertyTreeNode"] = None,
    ) -> None:
        self.messageHandler.warning(id, text, sourceFileInfo or self.property.sourceFileInfo)

    def info(
        self,
        id: str,
        text: str,
        sourceFileInfo: Optional[SourceFileInfo] = None,
        property_node: Optional["PropertyTreeNode"] = None,
    ) -> None:
        # Assuming info exists
        print(f"INFO: {text}")
