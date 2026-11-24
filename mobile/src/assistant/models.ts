export type ModelChoice = {
  id: string;
  sizeMb: number;
  selected: boolean;
  downloads: false;
  reason: string;
};

export const ON_DEVICE_MODELS: ModelChoice[] = [
  {
    id: "platform-speech-and-rules",
    sizeMb: 0,
    selected: true,
    downloads: false,
    reason: "Phone commands stay on the device. Speech uses the Android recognizer and no audio is uploaded continuously.",
  },
  {
    id: "whisper-tiny",
    sizeMb: 75,
    selected: false,
    downloads: false,
    reason: "Possible later offline transcription. Not downloaded.",
  },
  {
    id: "gemma-2b-q4",
    sizeMb: 1500,
    selected: false,
    downloads: false,
    reason: "Too large and too slow for always-on phone use. Not downloaded.",
  },
];

export function selectedModel(): ModelChoice {
  const selected = ON_DEVICE_MODELS.find((item) => item.selected);
  if (!selected || selected.downloads) throw new Error("NOVA must not select a model that downloads itself.");
  return selected;
}
