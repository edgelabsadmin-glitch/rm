export interface InboxEmailDTO {
  email_id: string;
  from_email: string;
  from_name: string | null;
  subject: string | null;
  snippet: string;
  received_at: string;
  account_id: string | null;
  tier: string | null;
  risk: "Low" | "Medium" | "High" | null;
  has_draft: boolean;
}

export interface InboxEmailDetailDTO extends InboxEmailDTO {
  body: string;
  suggested_reply: string | null;
  reply_rationale: string | null;
  draft_reply: string | null;
}

export interface InboxListDTO {
  emails: InboxEmailDTO[];
  count: number;
}

export type ReplyTone = "formal" | "shorter" | "warmer";
