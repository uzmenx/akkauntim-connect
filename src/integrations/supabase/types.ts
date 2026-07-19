export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      ai_signals: {
        Row: {
          confidence: number
          created_at: string
          executed: boolean
          id: string
          reasoning: string | null
          rejection_reason: string | null
          signal: string
          stop_loss_pips: number | null
          symbol: string
          take_profit_pips: number | null
          user_id: string
        }
        Insert: {
          confidence: number
          created_at?: string
          executed?: boolean
          id?: string
          reasoning?: string | null
          rejection_reason?: string | null
          signal: string
          stop_loss_pips?: number | null
          symbol: string
          take_profit_pips?: number | null
          user_id: string
        }
        Update: {
          confidence?: number
          created_at?: string
          executed?: boolean
          id?: string
          reasoning?: string | null
          rejection_reason?: string | null
          signal?: string
          stop_loss_pips?: number | null
          symbol?: string
          take_profit_pips?: number | null
          user_id?: string
        }
        Relationships: []
      }
      bot_settings: {
        Row: {
          ai_model: string
          created_at: string
          id: string
          max_daily_loss: number
          max_lot_size: number
          min_confidence: number
          mt5_login: string | null
          mt5_password: string | null
          mt5_server: string | null
          mt5_terminal_path: string | null
          risk_level_multiple_confirmation: number
          risk_level_single_confirmation: number
          risk_per_trade: number
          symbols: string[]
          system_prompt: string
          timeframe_major: string
          timeframe_minor: string
          updated_at: string
          user_id: string
        }
        Insert: {
          ai_model?: string
          created_at?: string
          id?: string
          max_daily_loss?: number
          max_lot_size?: number
          min_confidence?: number
          mt5_login?: string | null
          mt5_password?: string | null
          mt5_server?: string | null
          mt5_terminal_path?: string | null
          risk_level_multiple_confirmation?: number
          risk_level_single_confirmation?: number
          risk_per_trade?: number
          symbols?: string[]
          system_prompt?: string
          timeframe_major?: string
          timeframe_minor?: string
          updated_at?: string
          user_id: string
        }
        Update: {
          ai_model?: string
          created_at?: string
          id?: string
          max_daily_loss?: number
          max_lot_size?: number
          min_confidence?: number
          mt5_login?: string | null
          mt5_password?: string | null
          mt5_server?: string | null
          mt5_terminal_path?: string | null
          risk_level_multiple_confirmation?: number
          risk_level_single_confirmation?: number
          risk_per_trade?: number
          symbols?: string[]
          system_prompt?: string
          timeframe_major?: string
          timeframe_minor?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      bot_status: {
        Row: {
          account_balance: number | null
          account_currency: string | null
          account_equity: number | null
          broker: string | null
          created_at: string
          id: string
          is_running: boolean
          last_heartbeat: string | null
          message: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          account_balance?: number | null
          account_currency?: string | null
          account_equity?: number | null
          broker?: string | null
          created_at?: string
          id?: string
          is_running?: boolean
          last_heartbeat?: string | null
          message?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          account_balance?: number | null
          account_currency?: string | null
          account_equity?: number | null
          broker?: string | null
          created_at?: string
          id?: string
          is_running?: boolean
          last_heartbeat?: string | null
          message?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      positions: {
        Row: {
          current_price: number | null
          id: string
          open_price: number
          opened_at: string
          profit: number | null
          side: string
          stop_loss: number | null
          symbol: string
          take_profit: number | null
          ticket: number
          updated_at: string
          user_id: string
          volume: number
        }
        Insert: {
          current_price?: number | null
          id?: string
          open_price: number
          opened_at?: string
          profit?: number | null
          side: string
          stop_loss?: number | null
          symbol: string
          take_profit?: number | null
          ticket: number
          updated_at?: string
          user_id: string
          volume: number
        }
        Update: {
          current_price?: number | null
          id?: string
          open_price?: number
          opened_at?: string
          profit?: number | null
          side?: string
          stop_loss?: number | null
          symbol?: string
          take_profit?: number | null
          ticket?: number
          updated_at?: string
          user_id?: string
          volume?: number
        }
        Relationships: []
      }
      trade_history: {
        Row: {
          close_price: number
          closed_at: string
          created_at: string
          id: string
          open_price: number
          opened_at: string
          profit: number
          side: string
          stop_loss: number | null
          symbol: string
          take_profit: number | null
          ticket: number
          user_id: string
          volume: number
        }
        Insert: {
          close_price: number
          closed_at?: string
          created_at?: string
          id?: string
          open_price: number
          opened_at: string
          profit?: number
          side: string
          stop_loss?: number | null
          symbol: string
          take_profit?: number | null
          ticket: number
          user_id: string
          volume: number
        }
        Update: {
          close_price?: number
          closed_at?: string
          created_at?: string
          id?: string
          open_price?: number
          opened_at?: string
          profit?: number
          side?: string
          stop_loss?: number | null
          symbol?: string
          take_profit?: number | null
          ticket?: number
          user_id?: string
          volume?: number
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
