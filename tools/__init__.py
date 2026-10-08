from registry import register_tool, Tool

from .calculator import calculator_node
from .greeting import greeting_tool
from .llm import llm_tool
from .rag import rag_tool
from .weather import weather_tool

print("Loading tools package...")

register_tool(
    Tool(
        name="calculator",
        function=calculator_node,
        description="Arithmetic calculations.",
        outputs=["value"],
    )
)

register_tool(
    Tool(
        name="rag",
        function=rag_tool,
        description="Answer questions using retrieved documents.",
        outputs=["answer"],
    )
)

register_tool(
    Tool(
        name="llm",
        function=llm_tool,
        description="General reasoning and summarization.",
        outputs=["answer"],
    )
)

register_tool(
    Tool(
        name="direct",
        function=greeting_tool,
        description="Greeting and casual conversation.",
        outputs=["answer"],
    )
)

register_tool(
    Tool(
        name="weather",
        function=weather_tool,
        description=(
            "Get current weather and today's precipitation "
            "probability for a specified location."
        ),
        outputs=[
            "location",
            "current",
            "precipitation_probability",
        ],
    )
)