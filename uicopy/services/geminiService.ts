import { GoogleGenAI, Type } from "@google/genai";
import { AnalysisResult } from "../types";

const SYSTEM_INSTRUCTION = `
You are an expert AI Photo Analyst specializing in extracting social clues, lifestyle indicators, and hidden details from images. 
Your goal is to provide a comprehensive analysis of a photo containing a person (who is not the user).

**LANGUAGE:** You must respond in **Simplified Chinese (简体中文)** for all descriptions and findings.

Analyze the image for the following categories:

1. **Lifestyle Clues:** Infer the lifestyle, social background, and consumption level based on the scene, items, and clothing.
2. **Hidden Details:** specific details like reflections, text on screens (OCR), background items, file artifacts, etc.
3. **Intention:** Judge the likely reason the photo was taken or posted (e.g., showing off, daily record, professional).
4. **Credibility:** Assess authenticity, potential filtering/editing, and EXIF-like visual clues (e.g., "looks like a phone camera").
5. **Person Estimation:** Estimate gender, height (relative to environment), and body type using *cautious, non-judgmental, probabilistic language* (e.g., "appears to be", "estimated").

**CRITICAL:** You must return the result in valid JSON format. Do not include markdown code blocks.
`;

const SCHEMA = {
  type: Type.OBJECT,
  properties: {
    lifestyle: {
      type: Type.OBJECT,
      properties: {
        description: { type: Type.STRING, description: "2-3 sentences summarizing lifestyle clues in Chinese." },
        tags: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              type: { type: Type.STRING, description: "Category like 'consumption', 'scene', 'object'" },
              tag: { type: Type.STRING, description: "The keyword in Chinese, e.g., '咖啡店', '高端'" }
            }
          }
        }
      }
    },
    details: {
      type: Type.OBJECT,
      properties: {
        description: { type: Type.STRING, description: "Summary of hidden details found in Chinese." },
        findings: { type: Type.ARRAY, items: { type: Type.STRING }, description: "List of specific observations with emoji prefixes in Chinese." }
      }
    },
    intention: {
      type: Type.OBJECT,
      properties: {
        description: { type: Type.STRING, description: "Analysis of why the photo was taken in Chinese." },
        category: { type: Type.STRING, description: "Short category in Chinese e.g., '炫耀', '日常记录', '职业照'" }
      }
    },
    credibility: {
      type: Type.OBJECT,
      properties: {
        description: { type: Type.STRING, description: "Assessment of photo authenticity in Chinese." },
        clues: { type: Type.ARRAY, items: { type: Type.STRING }, description: "List of technical clues about quality/editing in Chinese." },
        exif: {
            type: Type.OBJECT,
            properties: {
                camera: { type: Type.STRING, nullable: true },
                datetime: { type: Type.STRING, nullable: true },
                has_gps: { type: Type.BOOLEAN, nullable: true }
            },
            nullable: true
        }
      }
    },
    person: {
      type: Type.OBJECT,
      properties: {
        description: { type: Type.STRING, description: "Neutral summary of physical traits in Chinese." },
        gender: { type: Type.STRING, description: "Gender in Chinese" },
        estimated_height: { type: Type.STRING, description: "Estimated height in Chinese" },
        body_type: { type: Type.STRING, description: "Body type description in Chinese" }
      }
    }
  }
};

export const analyzeImage = async (base64Image: string): Promise<AnalysisResult> => {
  const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: {
        parts: [
          {
            inlineData: {
              mimeType: 'image/jpeg', 
              data: base64Image
            }
          },
          {
            text: "Analyze this image according to the system instructions and return JSON in Simplified Chinese."
          }
        ]
      },
      config: {
        systemInstruction: SYSTEM_INSTRUCTION,
        responseMimeType: "application/json",
        responseSchema: SCHEMA
      }
    });

    const text = response.text;
    if (!text) throw new Error("No response from AI");

    return JSON.parse(text) as AnalysisResult;
  } catch (error) {
    console.error("Analysis failed:", error);
    throw error;
  }
};