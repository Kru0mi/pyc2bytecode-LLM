# Note: This script only works for Python 3.12 .pyc files.
# Output files will be created in the same directory as the input .pyc file, with output filenames based on the input filename.

import sys
import marshal
import dis
import io
import os
import asyncio
import aiohttp

# --- OpenRouter API config (referenced from ocr_thread.py) ---
API_KEY = "YOUR-API-KEY-HERE"  # Replace with your OpenRouter API key
# Note: You can set this as an environment variable instead of hardcoding it.
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "google/gemini-2.0-flash-001"
# Improved prompt for better decompilation and asm meaning preservation
DECOMPILE_PROMPT = (
    "You are given Python 3.12 pyc disassembled bytecode below.\n"
    "Your task is to decompile it into a readable Python script that is as close as possible in logic and structure to the original bytecode (i.e., preserve the meaning and flow as seen in the assembly instructions).\n"
    "Do not add extra explanations, comments, or modifications beyond what is necessary to faithfully represent the bytecode logic in Python.\n"
    "After the code block, provide a step-by-step explanation of your decompilation process and highlight any key improvements or important points.\n"
    "\n"
    "{Input}"
)

async def call_openrouter_llm(api_key, prompt):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt}
                ]
            }
        ]
    }
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(OPENROUTER_API_URL, headers=headers, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            else:
                error_text = await response.text()
                print(f"OpenRouter API error: {response.status} - {error_text}")
                return None

def dump_dis_to_bin(code, bin_path):
    # Dump disassembled bytecode to a .bin file
    with io.StringIO() as buf:
        dis.dis(code, file=buf)
        asm_output = buf.getvalue()
    with open(bin_path, "w", encoding="utf-8") as f:
        f.write(asm_output)
    return asm_output

async def main():
    if len(sys.argv) != 2:
        print("Usage: python pyc2bytecode.py <file.pyc>")
        sys.exit(1)
    pyc_path = sys.argv[1]
    with open(pyc_path, "rb") as f:
        data = f.read()
    code = marshal.loads(data[16:])
    print(repr(code))
    print("Raw bytecode:", code.co_code)
    print("Disassembled (asm-like):")
    dis.dis(code)

    # Dump disassembled bytecode to .bin file
    bin_path = pyc_path.rsplit('.', 1)[0] + ".bin"
    asm_output = dump_dis_to_bin(code, bin_path)
    print(f"Disassembly written to {bin_path}")

    # Read .bin content to send to LLM
    with open(bin_path, "r", encoding="utf-8") as f:
        bin_content = f.read()
    # Add explain step and key improvement request to the prompt
    prompt = (
        "This is python 3.12 pyc byte code , i want you read all byte code and decompile to readable python script that close meaning to assembly pyc code\n"
        "After decompiling, please explain step by step how you did it and highlight key improvements or important points in the decompiled code.\n"
        "{Input}"
    ).replace("{Input}", bin_content)
    print("Sending to OpenRouter LLM for decompilation...")
    llm_result = await call_openrouter_llm(API_KEY, prompt)
    if llm_result:
        print("\n--- LLM Decompile Result ---\n")
        print(llm_result)
        # Output files will be named based on the input file
        base_name = os.path.splitext(os.path.basename(pyc_path))[0]
        code_path = os.path.join(os.path.dirname(pyc_path), f"{base_name}_LLM.py")
        readme_path = os.path.join(os.path.dirname(pyc_path), f"{base_name}_LLM_readme.md")
        is_code = False
        code_content = ""
        readme_content = ""
        llm_stripped = llm_result.strip()
        if llm_stripped.startswith("```python"):
            code_content = llm_stripped.split("```python",1)[1].rsplit("```",1)[0].strip()
            is_code = True
            # Extract explanation after code block if present
            after_code = llm_stripped.split("```python",1)[1].rsplit("```",1)
            if len(after_code) > 1:
                readme_content = after_code[1].strip()
        elif llm_stripped.startswith("```"):
            code_content = llm_stripped.split("```",1)[1].rsplit("```",1)[0].strip()
            is_code = True
            after_code = llm_stripped.split("```",1)[1].rsplit("```",1)
            if len(after_code) > 1:
                readme_content = after_code[1].strip()
        elif llm_stripped.startswith("def ") or llm_stripped.startswith("class ") or llm_stripped.startswith("import "):
            code_content = llm_stripped
            is_code = True

        if is_code and code_content:
            with open(code_path, "w", encoding="utf-8") as f:
                f.write(code_content)
            print(f"Python code written to {code_path}")
            # If there is explanation after code, write it to readme
            if readme_content:
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(readme_content)
                print(f"Explanation written to {readme_path}")
        elif not is_code:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(llm_stripped)
            print(f"Other content written to {readme_path}")
    else:
        print("Failed to get response from OpenRouter LLM.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
