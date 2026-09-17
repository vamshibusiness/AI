from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict


class State(TypedDict):
    message: str


def jarvis_node(state: State):
    print("Jarvis Agent: LangGraph is working!")
    return {"message": state["message"]}


graph_builder = StateGraph(State)

graph_builder.add_node("jarvis", jarvis_node)
graph_builder.add_edge(START, "jarvis")
graph_builder.add_edge("jarvis", END)

graph = graph_builder.compile()

result = graph.invoke({"message": "test"})

print("Result:", result)
print("LANGGRAPH TEST: PASS")
