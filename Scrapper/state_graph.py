from typing import Callable, Dict, Generic, TypeVar, Any, Optional

# A simple, dependency-free replacement for a minimal StateGraph used in the
# user's example. It supports adding nodes (agents), edges, conditional
# routing functions, setting an entry point and compiling to a runnable app.

T = TypeVar("T", bound=Dict[str, Any])

# END sentinel used by workflows to signal completion
END = "END"


class CompiledApp(Generic[T]):
    def __init__(self, graph: "StateGraph") -> None:
        self._graph = graph

    def invoke(self, state: T) -> T:
        current = self._graph.entry_point
        if current is None:
            state["status"] = "error: no entry point set"
            return state

        while current != END:
            if current not in self._graph.nodes:
                state["status"] = f"error: missing node {current}"
                return state

            agent = self._graph.nodes[current]
            result = agent(state)

            # If agent returned a dict, merge it into the state
            if isinstance(result, dict):
                state.update(result)

            # Conditional routing takes precedence
            if current in self._graph.conditional_funcs:
                next_node = self._graph.conditional_funcs[current](state)
            else:
                outs = self._graph.edges.get(current, [])
                next_node = outs[0] if outs else END

            if next_node is None or next_node == END:
                return state

            current = next_node

        return state


class StateGraph(Generic[T]):
    def __init__(self, state_type: Any = dict) -> None:
        self.nodes: Dict[str, Callable[[T], Dict[str, Any]]] = {}
        self.edges: Dict[str, list] = {}
        self.conditional_funcs: Dict[str, Callable[[T], Any]] = {}
        self.entry_point: Optional[str] = None

    def add_node(self, name: str, func: Callable[[T], Dict[str, Any]]) -> None:
        self.nodes[name] = func

    def set_entry_point(self, name: str) -> None:
        self.entry_point = name

    def add_edge(self, src: str, dst: str) -> None:
        self.edges.setdefault(src, []).append(dst)

    def add_conditional_edges(self, src: str, cond_func: Callable[[T], Any]) -> None:
        self.conditional_funcs[src] = cond_func

    def compile(self) -> CompiledApp[T]:
        return CompiledApp(self)
