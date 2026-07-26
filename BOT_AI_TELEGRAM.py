import os
import requests
import json
from pydantic import BaseModel, Field
from crewai import Agent, Crew, Task

# استيراد BaseTool بمرونة كاملة تتوافق مع إصدارات CrewAI المختلفة على Python 3.14
BaseTool = None

try:
    from crewai.tools import BaseTool
except ImportError:
    pass

if BaseTool is None:
    try:
        from crewai.tools.base_tool import BaseTool
    except ImportError:
        pass

if BaseTool is None:
    try:
        from crewai.tools.structured_tool import CrewStructuredTool as BaseTool
    except ImportError:
        pass

if BaseTool is None:
    try:
        # المسار الحديث في إصدارات CrewAI الأخيرة
        from crewai.tools.base_tool import Tool as BaseTool
    except ImportError:
        # Fallback لـ LangChain BaseTool إذا تعذر الوصول لـ CrewAI
        from langchain.tools import BaseTool

# =====================================================================
# 1. أدوات البحث والإنترنت (Web & Search Tools)
# =====================================================================

class GoogleSerperInput(BaseModel):
    query: str = Field(..., description="نص البحث المراد الاستعلام عنه في Google")

class GoogleSerperSearchTool(BaseTool):
    name: str = "Google Serper Search"
    description: str = "Searches Google using the Serper API and returns a summary of snippets."
    args_schema: type[BaseModel] = GoogleSerperInput

    def _run(self, query: str="", **kwargs) -> str:
        import requests
        api_key = os.environ.get("SERPER_API_KEY")
        if not api_key:
            return "Error: SERPER_API_KEY environment variable not set."
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        payload = json.dumps({"q": query})
        try:
            response = requests.post(url, headers=headers, data=payload)
            results = response.json()
            snippets = [item.get("snippet", "") for item in results.get("organic", [])]
            return "\n\n".join(snippets) if snippets else "No results found."
        except Exception as e:
            return f"Error during search: {str(e)}"

google_serper_search = GoogleSerperSearchTool()

os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"
os.environ["OPENAI_MODEL_NAME"] = "llama-3.1-8b-instant"

url_tele = "https://api.telegram.org/bot8909625857:AAGs5ViLQ41HD-oEXxBe3wGwtHVCz442Hv8/getUpdates"
url_send = "https://api.telegram.org/bot8909625857:AAGs5ViLQ41HD-oEXxBe3wGwtHVCz442Hv8/sendMessage"

id = None

# تفريغ الرسائل القديمة فور بدء التشغيل
init_updates = requests.get(url_tele).json().get("result", [])
if init_updates:
  id = init_updates[-1]["update_id"] + 1

print("🚀 البوت جاهز ومستني الرسائل...")

while True:

  data = requests.get(url_tele, params={"offset": id, "timeout": 30}).json()
  print(1)
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

      # === AGENTS ===
      agent1 = Agent(
          role="Senior Academic Researcher",
          goal=f"Gather accurate, deep, and factual research ONLY about the topic: {topic}",
          backstory=(
              f"You are an expert academic researcher. Your only job is to collect accurate,"
              f" comprehensive facts, context, and key details about the user's specific topic: '{topic}'."
              " Do not search or gather info about unrelated subjects."
          ),
          allow_delegation=False,
          verbose=False,
          max_iter=1,
          tools=[google_serper_search]
      )

      agent2 = Agent(
          role="Professional Arabic Content Creator",
          goal=f"Write an insightful, beautifully formatted Arabic article exclusively about {topic}.",
          backstory=(
              "You are a native Arabic editor and writer. You write eloquent, high-quality Arabic"
              " articles using modern standard Arabic (فصحى حديثة وسلسة)."
              " You strictly follow topic boundaries and NEVER add any system notes or English text."
          ),
          allow_delegation=False,
          verbose=False,
          tools=[]
      )

      # === TASKS ===
      task1 = Task(
          description=(
              f"Search for deep and accurate details strictly on the topic: '{topic}'.\n"
              "Extract key definitions, historical facts, and core insights.\n"
              "Ensure all gathered info belongs ONLY to this topic."
          ),
          expected_output=f"Detailed factual research notes about '{topic}'.",
          agent=agent1,
      )

      task2 = Task(
          description=(
              f"Read the research findings and write a complete, elegant Arabic article strictly about '{topic}'.\n\n"
              "STRICT OUTPUT RULES:\n"
              f"1. SUBJECT LOCK: The entire article MUST be strictly about '{topic}'. Do not shift to any other topic.\n"
              "2. PURE ARABIC ONLY: Output ONLY Arabic text. Absolutely ZERO English words, intros, or conversational filler.\n"
              "3. NO SYSTEM NOTES: Do NOT add any notes at the end (e.g., NEVER write 'Note:', 'I corrected...', or 'Here is the article').\n"
              "4. START DIRECTLY: Begin immediately with the Title header (#).\n"
              "5. MARKDOWN STRUCTURE:\n"
              "   - # Title\n"
              "   - Brief Intro\n"
              "   - ## Subheadings for main ideas\n"
              "   - Bullet points for facts\n"
              "   - Strong Conclusion\n"
              "6. End immediately after the conclusion paragraph."
          ),
          expected_output=f"A clean Arabic article strictly about '{topic}', starting with '#' and containing zero English or notes.",
          agent=agent2,
      )

      # === CREW ===
      # تم تعطيل الـ verbose هنا أيضاً لإخفاء أي مخرجات جانبية للـ Tools
      crew = Crew(
          agents=[agent1, agent2],
          tasks=[task1, task2],
          verbose=False
      )

      print("\nجاري تشغيل الـ Crew...")
      result = crew.kickoff()

      print("\n تم الانتهاء بنجاح!")

      webhook="https://n8n-production-f84c2.up.railway.app/webhook-test/09445cfc-c700-455a-a682-cd9ccfcccb81"

      send_webhook = requests.post(webhook, json={"output":str(result)})

"""
      # إرسال النتيجة للتيليجرام
      final_send = {
          "chat_id": last_msg["message"]["chat"]["id"],
          "text": str(result),
          "parse_mode": "Markdown",
      }
      requests.post(url_send, json=final_send, timeout=15)
"""
