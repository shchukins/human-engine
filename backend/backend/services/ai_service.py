from __future__ import annotations

import httpx
import json

from backend.config import settings


class AIServiceError(Exception):
    pass


class AIService:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.default_model = settings.ollama_model
        self.fallback_model = settings.ollama_fallback_model
        self.timeout = settings.ollama_timeout_seconds

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        use_fallback: bool = True,
    ) -> dict[str, str]:
        selected_model = model or self.default_model
        full_prompt = self._build_prompt(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        try:
            return await self._call_ollama(
                model=selected_model,
                prompt=full_prompt,
            )
        except Exception as exc:
            if use_fallback and selected_model != self.fallback_model:
                return await self._call_ollama(
                    model=self.fallback_model,
                    prompt=full_prompt,
                )
            raise AIServiceError(f"AI generation failed: {exc}") from exc

    async def task_from_idea(self, idea: str) -> dict[str, str]:
        system_prompt = (
            "You are an assistant for the Human Engine project. "
            "Convert raw ideas into structured task descriptions for product and engineering work. "
            "You must stay strictly within the information provided by the user. "
            "Do not invent features, UI details, integrations, data sources, channels, screens, metrics, update logic, personalization, or business rules that were not explicitly stated. "
            "If some detail is missing, keep it generic and do not fill the gap with assumptions."
        )

        prompt = f"""
Convert the idea into a short structured task.

Strict rules:
- Use only information explicitly present in the idea.
- Do not add assumptions.
- Do not mention specific screens, pages, dashboards, notifications, APIs, integrations, user preferences, historical data, or dynamic updates unless explicitly mentioned.
- Keep the wording generic where details are missing.
- Acceptance Criteria must be minimal and directly traceable to the idea.
- Write exactly 3 acceptance criteria.
- Each acceptance criterion must be one sentence.

Required output format:
Title:
Goal:
Description:
Acceptance Criteria:
1.
2.
3.

Idea:
{idea}
""".strip()

    async def explain_metric(
        self,
        metric_name: str,
        metric_value: str | None = None,
        context: str | None = None,
    ) -> dict[str, str]:
        system_prompt = (
            "You are an assistant for the Human Engine project. "
            "Explain metrics in simple, clear language. "
            "Use only the information explicitly provided by the user. "
            "Do not invent formulas, thresholds, physiology, medical meaning, or hidden logic. "
            "If context is missing, keep the explanation generic and say only what can be safely inferred."
        )

        prompt = f"""
Explain the metric in a short structured way.

Rules:
- Use only the provided inputs.
- Do not invent physiology, formulas, thresholds, or recommendations unless explicitly present in the context.
- Keep the explanation concise and practical.
- Write in plain language.
- If the value is provided, explain how to read it only within the given context.
- If the context is missing, avoid assumptions.

Required output format:
Metric:
Current Value:
Meaning:
Interpretation:

Metric name:
{metric_name}

Metric value:
{metric_value or "not provided"}

Context:
{context or "not provided"}
""".strip()

        return await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        return await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

    async def task_from_idea_json(self, idea: str) -> dict:
        system_prompt = (
            "You are an assistant for the Human Engine project. "
            "Convert raw ideas into structured task descriptions. "
            "Return only valid JSON. "
            "Do not add markdown. "
            "Do not add explanations outside JSON. "
            "Use only information explicitly present in the idea. "
            "Do not invent features, screens, integrations, channels, APIs, preferences, or hidden logic."
        )

        prompt = f"""
Convert the idea into JSON.

Strict rules:
- Output must be valid JSON only.
- No markdown.
- No code fences.
- Use only information explicitly present in the idea.
- Do not add assumptions.
- acceptance_criteria must contain exactly 3 items.
- Each acceptance criterion must be short and directly traceable to the idea.

Return JSON with this exact structure:
{{
  "title": "string",
  "goal": "string",
  "description": "string",
  "acceptance_criteria": ["string", "string", "string"]
}}

Idea:
{idea}
""".strip()

        result = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        try:
            parsed = json.loads(result["response"])
        except json.JSONDecodeError as exc:
            raise AIServiceError(f"Invalid JSON from model: {exc}") from exc

        return {
            "model": result["model"],
            "data": parsed,
        }

    async def ride_briefing_json(
        self,
        readiness: str,
        readiness_context: str | None,
        weather_summary: str | None,
        training_suggestion: str | None,
        checklist: list[str] | None,
        extra_notes: str | None,
    ) -> dict:
        system_prompt = (
    "You are an assistant for the Human Engine project. "
    "Generate a concise ride briefing in Russian. "
    "Use only the provided inputs. "
    "Do not invent advice, recommendations, interpretations, or new facts. "
    "Do not infer clothing, intensity, safety guidance, or weather implications unless they are explicitly provided. "
    "Return only valid JSON and nothing else."
)

        prompt = f"""
Сформируй краткий ride briefing на русском языке.

Строгие правила:
- Ответ только в JSON.
- Без markdown и без пояснений вне JSON.
- Используй только переданные данные.
- Не добавляй новые советы, интерпретации или рекомендации.
- Не делай выводов из погоды, readiness или тренировки.
- Если поле содержит английский текст, переведи его на русский максимально буквально и нейтрально.
- Не изменяй смысл элементов checklist.
- Не заменяй элементы checklist на другие предметы.
- summary должно быть коротким объединением readiness, weather_summary и training_suggestion, без новых фактов.
- weather_note должно перефразировать только weather_summary.
- training_note должно перефразировать только training_suggestion.
- extra_note должно перефразировать только extra_notes.
- checklist должен содержать те же элементы, что пришли во входных данных.

Формат ответа:
{{
  "title": "string",
  "summary": "string",
  "weather_note": "string",
  "training_note": "string",
  "checklist": ["string"],
  "extra_note": "string"
}}

Данные:
readiness: {readiness}
readiness_context: {readiness_context or "not provided"}
weather_summary: {weather_summary or "not provided"}
training_suggestion: {training_suggestion or "not provided"}
checklist: {checklist or []}
extra_notes: {extra_notes or "not provided"}
""".strip()

        result = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        try:
            parsed = json.loads(result["response"])
        except json.JSONDecodeError as exc:
            raise AIServiceError(f"Invalid JSON from model: {exc}") from exc

        return {
            "model": result["model"],
            "data": parsed,
        }
    
    
    async def explain_metric_json(
        self,
        metric_name: str,
        metric_value: str | None = None,
        context: str | None = None,
    ) -> dict:
        system_prompt = (
            "You are an assistant for the Human Engine project. "
            "Explain metrics in simple and clear language. "
            "Return only valid JSON. "
            "Do not add markdown. "
            "Do not add explanations outside JSON. "
            "Use only the information explicitly provided by the user. "
            "Do not invent formulas, thresholds, physiology, medical meaning, or hidden logic."
        )

        prompt = f"""
Explain the metric and return JSON.

Strict rules:
- Output must be valid JSON only.
- No markdown.
- No code fences.
- Use only the provided inputs.
- If context is missing, keep the explanation generic.
- Do not invent formulas, thresholds, physiology, or recommendations.

Return JSON with this exact structure:
{{
  "metric": "string",
  "current_value": "string",
  "meaning": "string",
  "interpretation": "string"
}}

Metric name:
{metric_name}

Metric value:
{metric_value or "not provided"}

Context:
{context or "not provided"}
""".strip()

        result = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        try:
            parsed = json.loads(result["response"])
        except json.JSONDecodeError as exc:
            raise AIServiceError(f"Invalid JSON from model: {exc}") from exc

        return {
            "model": result["model"],
            "data": parsed,
        }
    
    def _build_prompt(self, prompt: str, system_prompt: str | None = None) -> str:
        if system_prompt:
            return f"System instruction:\n{system_prompt}\n\nUser request:\n{prompt}"
        return prompt

    async def _call_ollama(self, model: str, prompt: str) -> dict[str, str]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        if "response" not in data:
            raise AIServiceError("Ollama response does not contain 'response' field")

        return {
            "model": data.get("model", model),
            "response": data["response"].strip(),
        }


ai_service = AIService()
