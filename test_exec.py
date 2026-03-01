import asyncio
from nanobot.agent.tools.shell import ExecTool

async def main():
    tool = ExecTool(timeout=10)
    print("Testing 'python --version':")
    res1 = await tool.execute("python --version")
    print(repr(res1))
    
    print("\nTesting 'echo hello':")
    res2 = await tool.execute("echo hello")
    print(repr(res2))

if __name__ == "__main__":
    asyncio.run(main())
