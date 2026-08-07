export type FillMode = "search" | "url" | "manual";

export const SOURCE_TAG_CLASS: Record<string, string> = {
  reliable_secondary: "tag-rs",
  primary: "tag-primary",
  self_published: "tag-self",
  unreliable: "tag-unreliable",
};

export const SOURCE_TAG_LABEL: Record<string, string> = {
  reliable_secondary: "RS",
  primary: "Primary",
  self_published: "Self",
  unreliable: "Unreliable",
};

export const SLOT_LABELS: Record<string, string> = {
  full_name: "Full name",
  birth_date: "Date of birth",
  birth_place: "Place of birth",
  nationality: "Nationality",
  affiliation: "Institution",
  position: "Position / title",
  field: "Research field",
  education: "Education",
  known_for: "Known for",
  award: "Awards",
};

export const SLOT_HINTS: Record<string, string> = {
  birth_date:   "news article, obituary, or institutional bio",
  birth_place:  "news article or institutional bio",
  nationality:  "institutional bio or news",
  affiliation:  "institution website (faculty/staff page)",
  position:     "institution website (faculty/staff page)",
  field:        "institution website or research profile",
  education:    "institution website or CV/bio page",
  known_for:    "news article or research profile",
  award:        "press release, news, or institution website",
  full_name:    "institution website or official document",
};

export const SLOT_SECTIONS: { label: string; slots: string[] }[] = [
  { label: "Infobox", slots: ["full_name", "birth_date", "birth_place", "nationality"] },
  { label: "Career", slots: ["affiliation", "position", "field", "education"] },
  { label: "Recognition", slots: ["known_for", "award"] },
];
