import { GoogleGenAI, Type } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

export interface AssetMetadata {
  name: string;
  description: string;
  material: string;
  subject: string;
  style: string;
  estimatedComplexity: "low" | "medium" | "high";
}

export class GenAIService {
  /**
   * Analyzes an image (or URL) to extract metadata for 3D reconstruction.
   */
  static async analyzeImageForAsset(base64Image: string, mimeType: string): Promise<AssetMetadata> {
    const response = await ai.models.generateContent({
      model: "gemini-3.1-pro-preview",
      contents: [
        {
          parts: [
            {
              inlineData: {
                data: base64Image,
                mimeType: mimeType,
              },
            },
            {
              text: "Analyze this image and extract metadata for a 3D asset reconstruction. Provide the response in JSON format.",
            },
          ],
        },
      ],
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            name: { type: Type.STRING },
            description: { type: Type.STRING },
            material: { type: Type.STRING },
            subject: { type: Type.STRING },
            style: { type: Type.STRING },
            estimatedComplexity: { 
              type: Type.STRING,
              enum: ["low", "medium", "high"]
            },
          },
          required: ["name", "description", "material", "subject", "style", "estimatedComplexity"],
        },
      },
    });

    return JSON.parse(response.text || "{}");
  }

  /**
   * Generates a detailed prompt for a 3D asset generator based on a text description.
   */
  static async generateAssetPrompt(description: string): Promise<string> {
    const response = await ai.models.generateContent({
      model: "gemini-3.1-pro-preview",
      contents: `Generate a highly detailed technical prompt for a 3D asset generator (like a NeRF or Gaussian Splatting engine) based on this description: "${description}". Focus on geometry, texture maps, and material properties.`,
    });

    return response.text || "";
  }
}
