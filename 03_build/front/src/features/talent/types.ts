/* Talent (associate) DTOs — account-assigned talent, talent detail, and emails. */
import type { Priority, PriorityColor } from "@/features/analysis/types";

export interface TalentItem {
  associate_id: string;
  name: string | null;
  email: string | null;
  stage: string | null;
  priority: Priority | null;
  priority_color: PriorityColor | null;
}

export interface TalentDetail {
  associate_id: string;
  name: string | null;
  email: string | null;
  stage: string | null;
  account_id: string | null;
  account_name: string | null;
  tier: string | null;
  priority: Priority | null;
  priority_color: PriorityColor | null;
}

export interface TalentEmail {
  email_id: string;
  subject: string | null;
  body: string | null;
  received_at: string | null;
}

export interface EmailItem {
  email_id: string;
  from_email: string | null;
  from_name: string | null;
  subject: string | null;
  body: string | null;
  received_at: string | null;
  sender_kind: string | null;
}
