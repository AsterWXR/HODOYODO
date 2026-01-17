export interface Tag {
  type: string;
  tag: string;
}

export interface LifestyleAnalysis {
  description: string;
  tags: Tag[];
}

export interface DetailsAnalysis {
  description: string;
  findings: string[];
}

export interface IntentionAnalysis {
  description: string;
  category: string;
}

export interface CredibilityAnalysis {
  description: string;
  clues: string[];
  exif?: {
    camera?: string;
    datetime?: string;
    has_gps?: boolean;
  };
}

export interface PersonAnalysis {
  description: string;
  gender: string;
  estimated_height: string;
  body_type: string;
}

export interface AnalysisResult {
  lifestyle: LifestyleAnalysis;
  details: DetailsAnalysis;
  intention: IntentionAnalysis;
  credibility: CredibilityAnalysis;
  person: PersonAnalysis;
}

export enum AnalysisState {
  IDLE = 'IDLE',
  ANALYZING = 'ANALYZING',
  COMPLETE = 'COMPLETE',
  ERROR = 'ERROR',
}
