"""Run the compiled graph and return the final state."""

from v0_code.graph.builder import build_graph
from v0_code.graph.state import UMCState


async def run_pipeline(data_dir: str, ranges_dir: str, output_dir: str, glucose_caption_llm: bool = False) -> UMCState:
    app = build_graph()
    final = await app.ainvoke(
        UMCState(data_dir=data_dir, ranges_dir=ranges_dir, output_dir=output_dir, glucose_caption_llm=glucose_caption_llm)
    )
    return UMCState(**final)
