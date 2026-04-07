# mcp_server_mail.py
# Robust MCP server exposing safe, composable math + mail tools.
from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
from mcp.types import TextContent
from mcp import types
import os
import sys
from dotenv import load_dotenv
import ssl
import smtplib
from email.message import EmailMessage
import certifi
23
mcp = FastMCP("MailMCP")
load_dotenv()

# -------------------------------
# Basic math tools
# -------------------------------
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    print("CALLED: add(a: int, b: int) -> int")
    return int(a + b)

@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Subtract b from a and return the result."""
    print("CALLED: subtract(a: int, b: int) -> int")
    return int(a - b)

@mcp.tool()
def add_list(numbers: list[int]) -> int:
    """Return the sum of a list of integers.

    Example:
        add_list([1,2,3]) -> 6
    """
    print("CALLED: add_list(numbers: list[int]) -> int")
    return int(sum(int(x) for x in numbers))

@mcp.tool()
def fibonacci_numbers(n: int) -> list[int]:
    """Return the first n Fibonacci numbers as a list (starting [0, 1, ...])."""
    print("CALLED: fibonacci_numbers(n: int) -> list[int]")
    if n <= 0:
        return []
    fib = [0, 1]
    for _ in range(2, n):
        fib.append(fib[-1] + fib[-2])
    return fib[:n]

@mcp.tool()
def strings_to_chars_to_int(input_string: str, mode: int) -> list[int]:
    """Convert characters in a string to integers.

    mode = 0 -> ASCII code for each character
    mode = 1 -> Alphabet position for letters (A=1..Z=26), non-letters skipped
    Returns a list of integers.
    """
    print("CALLED: strings_to_chars_to_int(input_string: str, mode: int) -> list[int]")
    if mode == 0:
        return [ord(c) for c in input_string]
    elif mode == 1:
        return [(ord(c.upper()) - 64) for c in input_string if c.isalpha()]
    else:
        raise ValueError("Invalid mode. Use 0 for ASCII codes or 1 for alphabet positions.")

@mcp.tool()
def power_elements(values: list[int], exponent: int) -> list[int]:
    """Raise each integer in 'values' to 'exponent' and return the list.

    Example:
        power_elements([1,2,3], 2) -> [1, 4, 9]
    """
    print("CALLED: power_elements(values: list[int], exponent: int) -> list[int]")
    exp = int(exponent)
    return [int(v) ** exp for v in values]

# -------------------------------
# Mail tool
# -------------------------------
@mcp.tool()
def send_email(recipient_email: str, subject: str, body: str) -> str:
    # """Send an email via Gmail SMTP using app password.

    # Requires .env with:
    #     SENDER_EMAIL=you@gmail.com
    #     GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
    # """
    """
    Sends an email using the configured sender account.
    
    Parameters:
    - recipient (str): The recipient email address. This must be taken directly
      from the user’s query if they specify where to send the result.
    - subject (str): A short, clear subject line describing the purpose of the email.
    - body (str): The full message body. If a calculation or result was produced by
      other tools, the final computed result MUST be included in the body.
    
    Behavior:
    - This tool must be used whenever the user asks to "email", "send", or "share"
      the result with someone.
    - After the email is successfully sent, you can end the process.
    
    Returns:
    - Confirmation string that the email was sent.
    """
    print("CALLED: send_email(recipient_email: str, subject: str, body: str) -> str")
    sender = os.getenv("SENDER_EMAIL")
    password = os.getenv("GMAIL_APP_PASSWORD")
    if not sender or not password:
        return "Error: Email credentials (SENDER_EMAIL, GMAIL_APP_PASSWORD) not found in .env"

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient_email

    # Use certifi CA bundle to avoid certain corporate SSL issues.
    context = ssl.create_default_context(cafile=certifi.where())

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender, password)
            server.send_message(msg)
        return f"Email successfully sent to {recipient_email}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

# -------------------------------
# Resource + prompts
# -------------------------------
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Return a greeting string."""
    print("CALLED: get_greeting(name: str) -> str")
    return f"Hello, {name}!"

@mcp.prompt()
def review_code(code: str) -> str:
    print("CALLED: review_code(code: str) -> str")
    return f"Please review this code:\n\n{code}"

@mcp.prompt()
def debug_error(error: str) -> list[base.Message]:
    print("CALLED: debug_error(error: str) -> list[base.Message]")
    return [
        base.UserMessage("I'm seeing this error:"),
        base.UserMessage(error),
        base.AssistantMessage("I'll help debug that. What have you tried so far?"),
    ]

if __name__ == "__main__":
    # Check if running with `mcp dev`
    print("STARTING MailMCP server")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()  # No transport
    else:
        mcp.run(transport="stdio")