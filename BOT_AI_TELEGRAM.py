import os
import requests
import json
import warnings
warnings.filterwarnings("ignore")

from pydantic import BaseModel, Field
from crewai import Agent, Crew, Task
from crewai.tools import BaseTool

# =====================================================================
# 1. أدوات البحث والإنترنت (Web & Search Tools)
# =====================================================================

class GoogleSerperInput(BaseModel):
    query: str = Field(..., description="نص البحث المراد الاستعلام عنه في Google")

class GoogleSerperSearchTool(BaseTool):
    name: str = "Google Serper Search"
    description: str = "Searches Google using the Serper API and returns a summary of snippets."
    args_schema: type[BaseModel] = GoogleSerperInput

    def _run(self, query: str = "", **kwargs) -> str:
        api_key = os.environ.get("SERPER_API_KEY")
        if not api_key:
            return "Error: SERPER_API_KEY environment variable not set."
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        payload = json.dumps({"q": query})
        try:
            response = requests.post(url, headers=headers, data=payload, timeout=10)
            results = response.json()
            snippets = [item.get("snippet", "") for item in results.get("organic", [])]
            return "\n\n".join(snippets[:3]) if snippets else "No results found."
        except Exception as e:
            return f"Error during search: {str(e)}"

google_serper_search = GoogleSerperSearchTool()

os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"
os.environ["OPENAI_MODEL_NAME"] = "llama-3.1-8b-instant"

url_tele = "https://api.telegram.org/bot8909625857:AAGs5ViLQ41HD-oEXxBe3wGwtHVCz442Hv8/getUpdates"
url_send = "https://api.telegram.org/bot8909625857:AAGs5ViLQ41HD-oEXxBe3wGwtHVCz442Hv8/sendMessage"

print("🚀 البوت جاهز ومستني الرسائل...")

id = None
try:
    init_updates = requests.get(url_tele, timeout=10).json().get("result", [])
    if init_updates:
        id = init_updates[-1]["update_id"] + 1
except Exception:
    pass

while True:
    try:
        data = requests.get(url_tele, params={"offset": id, "timeout": 30}, timeout=35).json()

        if data.get("result"):
            last_msg = data["result"][-1]
            id = last_msg["update_id"] + 1

            if "text" in last_msg.get("message", {}):
                topic = last_msg["message"]["text"]
                print(f"\n📩 يتم معالجة موضوع: {topic}")

                info = {
                    "chat_id": last_msg["message"]["chat"]["id"],
                    "text": "الرجاء الإنتظار قليلًا، يتم إنشاء بحثك الآن بأعلى جودة...",
                    "parse_mode": "Markdown",
                }
                requests.post(url_send, json=info, timeout=10)

                agent1 = Agent(
                    role="Senior Academic Researcher",
                    goal=f"Gather accurate research ONLY about: {topic}",
                    backstory=f"Academic researcher collecting facts about '{topic}'.",
                    allow_delegation=False,
                    verbose=False,
                    max_iter=1,
                    max_execution_time=30,
                    tools=[google_serper_search]
                )

                agent2 = Agent(
                    role="Professional Arabic Content Creator",
                    goal=f"Write an Arabic article exclusively about {topic}.",
                    backstory="Native Arabic editor writing eloquent high-quality Arabic articles.",
                    allow_delegation=False,
                    verbose=False,
                    max_iter=1,
                    max_execution_time=30,
                    tools=[]
                )

                task1 = Task(
                    description=f"Search for deep and accurate details strictly on the topic: '{topic}'.",
                    expected_output=f"Detailed factual research notes about '{topic}'.",
                    agent=agent1,
                )

                task2 = Task(
                    description=(
                        f"Read the research findings and write a complete, elegant Arabic article strictly about '{topic}'.\n\n"
                        "STRICT OUTPUT RULES:\n"
                        f"1. SUBJECT LOCK: Entire article MUST be about '{topic}'.\n"
                        "2. PURE ARABIC ONLY: Output ONLY Arabic text. Absolutely ZERO English words.\n"
                        "3. NO SYSTEM NOTES: Do NOT add any notes at the end.\n"
                        "4. START DIRECTLY: Begin immediately with Header (#)."
                    ),
                    expected_output=f"A clean Arabic article strictly about '{topic}'.",
                    agent=agent2,
                )

                crew = Crew(
                    agents=[agent1, agent2],
                    tasks=[task1, task2],
                    verbose=False
                )

                print("\nجاري تشغيل الـ Crew...")
                result = crew.kickoff()
                print("\n تم الانتهاء بنجاح!")

                # 1. إرسال للتيليجرام
                final_send = {
                    "chat_id": last_msg["message"]["chat"]["id"],
                    "text": str(result),
                    "parse_mode": "Markdown"
                }
                requests.post(url_send, json=final_send, timeout=15)

                # 2. إرسال لـ Webhook n8n
                webhook = "https://n8n-production-f84c2.up.railway.app/webhook/09445cfc-c700-455a-a682-cd9ccfcccb81"
                try:
                    requests.post(webhook, json={"output": str(result)}, timeout=10)
                    print("تم إرسال النتيجة لـ n8n بنجاح!")
                except Exception as e:
                    print(f"n8n webhook error: {e}")

    except Exception as outer_e:
        print(f"Loop error caught: {outer_e}")
