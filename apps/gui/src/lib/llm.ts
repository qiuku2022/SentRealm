import type { LlmKeyStatus, Settings } from "@/lib/types";

/** True when preprocess will invoke the LLM break step (matches core is_llm_configured). */
export function isLlmProcessingEnabled(
  settings: Settings | null,
  llmKeyStatus: LlmKeyStatus,
): boolean {
  if (!settings?.llm_enabled) return false;
  if (!llmKeyStatus.configured) return false;
  if (!settings.llm_endpoint.trim()) return false;
  if (!settings.llm_model.trim()) return false;
  return true;
}
