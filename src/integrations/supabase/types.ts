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
      ai_memory: {
        Row: {
          category: string | null
          created_at: string | null
          failed_applications: number | null
          id: string
          importance: number | null
          lesson_text: string
          source: string | null
          success_applications: number | null
          updated_at: string | null
        }
        Insert: {
          category?: string | null
          created_at?: string | null
          failed_applications?: number | null
          id?: string
          importance?: number | null
          lesson_text: string
          source?: string | null
          success_applications?: number | null
          updated_at?: string | null
        }
        Update: {
          category?: string | null
          created_at?: string | null
          failed_applications?: number | null
          id?: string
          importance?: number | null
          lesson_text?: string
          source?: string | null
          success_applications?: number | null
          updated_at?: string | null
        }
        Relationships: []
      }
      ai_signals: {
        Row: {
          confidence: number
          created_at: string
          entry_price: number | null
          executed: boolean
          id: string
          reasoning: string | null
          rejection_reason: string | null
          rr_ratio: number | null
          signal: string
          sl_price: number | null
          stop_loss_pips: number | null
          symbol: string
          take_profit_pips: number | null
          tp_price: number | null
          user_id: string
        }
        Insert: {
          confidence: number
          created_at?: string
          entry_price?: number | null
          executed?: boolean
          id?: string
          reasoning?: string | null
          rejection_reason?: string | null
          rr_ratio?: number | null
          signal: string
          sl_price?: number | null
          stop_loss_pips?: number | null
          symbol: string
          take_profit_pips?: number | null
          tp_price?: number | null
          user_id: string
        }
        Update: {
          confidence?: number
          created_at?: string
          entry_price?: number | null
          executed?: boolean
          id?: string
          reasoning?: string | null
          rejection_reason?: string | null
          rr_ratio?: number | null
          signal?: string
          sl_price?: number | null
          stop_loss_pips?: number | null
          symbol?: string
          take_profit_pips?: number | null
          tp_price?: number | null
          user_id?: string
        }
        Relationships: []
      }
      auto_patterns: {
        Row: {
          confidence: number | null
          formed_at: string
          id: string
          pattern_type: string
          signal: string
          status: string
          symbol: string
          timeframe: string
          updated_at: string
          user_id: string
        }
        Insert: {
          confidence?: number | null
          formed_at?: string
          id?: string
          pattern_type: string
          signal: string
          status?: string
          symbol: string
          timeframe: string
          updated_at?: string
          user_id: string
        }
        Update: {
          confidence?: number | null
          formed_at?: string
          id?: string
          pattern_type?: string
          signal?: string
          status?: string
          symbol?: string
          timeframe?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      backtest_jobs: {
        Row: {
          created_at: string
          id: string
          mode: string
          status: string
          strategy: string | null
          symbol: string
          timeframe: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          id?: string
          mode: string
          status?: string
          strategy?: string | null
          symbol: string
          timeframe: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          id?: string
          mode?: string
          status?: string
          strategy?: string | null
          symbol?: string
          timeframe?: string
          updated_at?: string
        }
        Relationships: []
      }
      bot_settings: {
        Row: {
          ai_enabled: boolean | null
          ai_model: string
          created_at: string
          id: string
          loop_interval_minutes: number | null
          loop_interval_seconds: number
          max_daily_loss: number
          max_lot_size: number
          min_confidence: number
          mt5_login: string | null
          mt5_password: string | null
          mt5_server: string | null
          mt5_terminal_path: string | null
          news_breakout_grid_enabled: boolean | null
          prompt_identity: string | null
          prompt_output: string | null
          prompt_strategy: string | null
          prompt_temporary: string | null
          prompt_temporary_expires_at: string | null
          realtime_enabled: boolean
          risk_level_multiple_confirmation: number
          risk_level_single_confirmation: number
          risk_per_trade: number
          shadow_mode: boolean | null
          strategy_weight_news: number | null
          strategy_weight_pattern: number | null
          strategy_weight_smc: number | null
          symbols: string[]
          system_prompt: string
          timeframe_major: string
          timeframe_minor: string
          updated_at: string
          user_id: string
        }
        Insert: {
          ai_enabled?: boolean | null
          ai_model?: string
          created_at?: string
          id?: string
          loop_interval_minutes?: number | null
          loop_interval_seconds?: number
          max_daily_loss?: number
          max_lot_size?: number
          min_confidence?: number
          mt5_login?: string | null
          mt5_password?: string | null
          mt5_server?: string | null
          mt5_terminal_path?: string | null
          news_breakout_grid_enabled?: boolean | null
          prompt_identity?: string | null
          prompt_output?: string | null
          prompt_strategy?: string | null
          prompt_temporary?: string | null
          prompt_temporary_expires_at?: string | null
          realtime_enabled?: boolean
          risk_level_multiple_confirmation?: number
          risk_level_single_confirmation?: number
          risk_per_trade?: number
          shadow_mode?: boolean | null
          strategy_weight_news?: number | null
          strategy_weight_pattern?: number | null
          strategy_weight_smc?: number | null
          symbols?: string[]
          system_prompt?: string
          timeframe_major?: string
          timeframe_minor?: string
          updated_at?: string
          user_id: string
        }
        Update: {
          ai_enabled?: boolean | null
          ai_model?: string
          created_at?: string
          id?: string
          loop_interval_minutes?: number | null
          loop_interval_seconds?: number
          max_daily_loss?: number
          max_lot_size?: number
          min_confidence?: number
          mt5_login?: string | null
          mt5_password?: string | null
          mt5_server?: string | null
          mt5_terminal_path?: string | null
          news_breakout_grid_enabled?: boolean | null
          prompt_identity?: string | null
          prompt_output?: string | null
          prompt_strategy?: string | null
          prompt_temporary?: string | null
          prompt_temporary_expires_at?: string | null
          realtime_enabled?: boolean
          risk_level_multiple_confirmation?: number
          risk_level_single_confirmation?: number
          risk_per_trade?: number
          shadow_mode?: boolean | null
          strategy_weight_news?: number | null
          strategy_weight_pattern?: number | null
          strategy_weight_smc?: number | null
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
          available_symbols: Json | null
          broker: string | null
          claude_limit: number
          claude_used: number
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
          available_symbols?: Json | null
          broker?: string | null
          claude_limit?: number
          claude_used?: number
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
          available_symbols?: Json | null
          broker?: string | null
          claude_limit?: number
          claude_used?: number
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
      candles: {
        Row: {
          close: number
          high: number
          id: string
          low: number
          open: number
          symbol: string
          time: string
          timeframe: string
          user_id: string
          volume: number | null
        }
        Insert: {
          close: number
          high: number
          id?: string
          low: number
          open: number
          symbol: string
          time: string
          timeframe: string
          user_id: string
          volume?: number | null
        }
        Update: {
          close?: number
          high?: number
          id?: string
          low?: number
          open?: number
          symbol?: string
          time?: string
          timeframe?: string
          user_id?: string
          volume?: number | null
        }
        Relationships: []
      }
      harmonic_patterns: {
        Row: {
          confidence: number | null
          entry_zone: Json | null
          formed_at: string
          id: string
          pattern_type: string
          signal: string
          sl: number | null
          status: string
          symbol: string
          timeframe: string
          tp_zones: Json | null
          updated_at: string
          user_id: string
        }
        Insert: {
          confidence?: number | null
          entry_zone?: Json | null
          formed_at?: string
          id?: string
          pattern_type: string
          signal: string
          sl?: number | null
          status?: string
          symbol: string
          timeframe: string
          tp_zones?: Json | null
          updated_at?: string
          user_id: string
        }
        Update: {
          confidence?: number | null
          entry_zone?: Json | null
          formed_at?: string
          id?: string
          pattern_type?: string
          signal?: string
          sl?: number | null
          status?: string
          symbol?: string
          timeframe?: string
          tp_zones?: Json | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      password_reset_tokens: {
        Row: {
          created_at: string
          expires_at: string
          id: string
          mt5_login: string
          success: boolean
          token_hash: string | null
          used_at: string | null
          user_id: string | null
        }
        Insert: {
          created_at?: string
          expires_at?: string
          id?: string
          mt5_login: string
          success?: boolean
          token_hash?: string | null
          used_at?: string | null
          user_id?: string | null
        }
        Update: {
          created_at?: string
          expires_at?: string
          id?: string
          mt5_login?: string
          success?: boolean
          token_hash?: string | null
          used_at?: string | null
          user_id?: string | null
        }
        Relationships: []
      }
      pending_books: {
        Row: {
          created_at: string | null
          file_name: string
          file_url: string
          id: string
          status: string | null
        }
        Insert: {
          created_at?: string | null
          file_name: string
          file_url: string
          id?: string
          status?: string | null
        }
        Update: {
          created_at?: string | null
          file_name?: string
          file_url?: string
          id?: string
          status?: string | null
        }
        Relationships: []
      }
      pending_orders: {
        Row: {
          created_at: string
          id: string
          price: number
          stop_loss: number | null
          symbol: string
          take_profit: number | null
          ticket: number
          type: string
          updated_at: string
          user_id: string
          volume: number
        }
        Insert: {
          created_at?: string
          id?: string
          price: number
          stop_loss?: number | null
          symbol: string
          take_profit?: number | null
          ticket: number
          type: string
          updated_at?: string
          user_id: string
          volume: number
        }
        Update: {
          created_at?: string
          id?: string
          price?: number
          stop_loss?: number | null
          symbol?: string
          take_profit?: number | null
          ticket?: number
          type?: string
          updated_at?: string
          user_id?: string
          volume?: number
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
      shadow_candles: {
        Row: {
          close: number
          created_at: string
          high: number
          id: string
          low: number
          open: number
          open_time: string
          symbol: string
          timeframe: string
          updated_at: string
          volume: number | null
        }
        Insert: {
          close: number
          created_at?: string
          high: number
          id?: string
          low: number
          open: number
          open_time: string
          symbol: string
          timeframe: string
          updated_at?: string
          volume?: number | null
        }
        Update: {
          close?: number
          created_at?: string
          high?: number
          id?: string
          low?: number
          open?: number
          open_time?: string
          symbol?: string
          timeframe?: string
          updated_at?: string
          volume?: number | null
        }
        Relationships: []
      }
      shadow_outcomes: {
        Row: {
          created_at: string
          evaluated_at: string
          id: string
          n_candles: number
          pips_result: number | null
          price_after_n_candles: number
          price_at_signal: number
          signal_id: string
          updated_at: string
          was_correct: boolean
        }
        Insert: {
          created_at?: string
          evaluated_at?: string
          id?: string
          n_candles?: number
          pips_result?: number | null
          price_after_n_candles: number
          price_at_signal: number
          signal_id: string
          updated_at?: string
          was_correct: boolean
        }
        Update: {
          created_at?: string
          evaluated_at?: string
          id?: string
          n_candles?: number
          pips_result?: number | null
          price_after_n_candles?: number
          price_at_signal?: number
          signal_id?: string
          updated_at?: string
          was_correct?: boolean
        }
        Relationships: [
          {
            foreignKeyName: "shadow_outcomes_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: true
            referencedRelation: "shadow_signals"
            referencedColumns: ["id"]
          },
        ]
      }
      shadow_signals: {
        Row: {
          candle_time: string
          created_at: string
          features: Json
          id: string
          score: number
          signal: string
          symbol: string
          timeframe: string
          updated_at: string
        }
        Insert: {
          candle_time: string
          created_at?: string
          features?: Json
          id?: string
          score: number
          signal: string
          symbol: string
          timeframe: string
          updated_at?: string
        }
        Update: {
          candle_time?: string
          created_at?: string
          features?: Json
          id?: string
          score?: number
          signal?: string
          symbol?: string
          timeframe?: string
          updated_at?: string
        }
        Relationships: []
      }
      smc_zones: {
        Row: {
          bottom: number
          direction: string
          formed_at: string
          id: string
          status: string
          symbol: string
          timeframe: string
          top: number
          updated_at: string
          user_id: string
          zone_type: string
        }
        Insert: {
          bottom: number
          direction: string
          formed_at: string
          id?: string
          status?: string
          symbol: string
          timeframe: string
          top: number
          updated_at?: string
          user_id: string
          zone_type: string
        }
        Update: {
          bottom?: number
          direction?: string
          formed_at?: string
          id?: string
          status?: string
          symbol?: string
          timeframe?: string
          top?: number
          updated_at?: string
          user_id?: string
          zone_type?: string
        }
        Relationships: []
      }
      sr_volume_zones: {
        Row: {
          formed_at: string
          id: string
          price: number
          status: string
          strength: number | null
          symbol: string
          timeframe: string
          type: string
          updated_at: string
          user_id: string
        }
        Insert: {
          formed_at?: string
          id?: string
          price: number
          status?: string
          strength?: number | null
          symbol: string
          timeframe: string
          type: string
          updated_at?: string
          user_id: string
        }
        Update: {
          formed_at?: string
          id?: string
          price?: number
          status?: string
          strength?: number | null
          symbol?: string
          timeframe?: string
          type?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      strategy_insights: {
        Row: {
          created_at: string | null
          fail_count: number | null
          id: string
          insight_text: string
          market_condition: string | null
          setup_type: string | null
          success_count: number | null
        }
        Insert: {
          created_at?: string | null
          fail_count?: number | null
          id?: string
          insight_text: string
          market_condition?: string | null
          setup_type?: string | null
          success_count?: number | null
        }
        Update: {
          created_at?: string | null
          fail_count?: number | null
          id?: string
          insight_text?: string
          market_condition?: string | null
          setup_type?: string | null
          success_count?: number | null
        }
        Relationships: []
      }
      strategy_performance: {
        Row: {
          avg_rr: number | null
          id: string
          losses: number | null
          recommended_weight: number | null
          strategy_name: string
          total_profit: number | null
          updated_at: string | null
          wins: number | null
        }
        Insert: {
          avg_rr?: number | null
          id?: string
          losses?: number | null
          recommended_weight?: number | null
          strategy_name: string
          total_profit?: number | null
          updated_at?: string | null
          wins?: number | null
        }
        Update: {
          avg_rr?: number | null
          id?: string
          losses?: number | null
          recommended_weight?: number | null
          strategy_name?: string
          total_profit?: number | null
          updated_at?: string | null
          wins?: number | null
        }
        Relationships: []
      }
      system_meta: {
        Row: {
          key: string
          updated_at: string | null
          value: string | null
        }
        Insert: {
          key: string
          updated_at?: string | null
          value?: string | null
        }
        Update: {
          key?: string
          updated_at?: string | null
          value?: string | null
        }
        Relationships: []
      }
      test_results: {
        Row: {
          created_at: string
          id: string
          reasoning: string | null
          symbol: string
          timeframe: string
          total_profit: number
          total_trades: number
          type: string
          win_rate: number
        }
        Insert: {
          created_at?: string
          id?: string
          reasoning?: string | null
          symbol: string
          timeframe: string
          total_profit?: number
          total_trades?: number
          type: string
          win_rate?: number
        }
        Update: {
          created_at?: string
          id?: string
          reasoning?: string | null
          symbol?: string
          timeframe?: string
          total_profit?: number
          total_trades?: number
          type?: string
          win_rate?: number
        }
        Relationships: []
      }
      trade_history: {
        Row: {
          agreed_strategies: string[] | null
          ai_used: boolean | null
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
          agreed_strategies?: string[] | null
          ai_used?: boolean | null
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
          agreed_strategies?: string[] | null
          ai_used?: boolean | null
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
      wyckoff_events: {
        Row: {
          confidence: number | null
          formed_at: string
          id: string
          phase: string
          signal: string
          status: string
          symbol: string
          timeframe: string
          updated_at: string
          user_id: string
        }
        Insert: {
          confidence?: number | null
          formed_at?: string
          id?: string
          phase: string
          signal: string
          status?: string
          symbol: string
          timeframe: string
          updated_at?: string
          user_id: string
        }
        Update: {
          confidence?: number | null
          formed_at?: string
          id?: string
          phase?: string
          signal?: string
          status?: string
          symbol?: string
          timeframe?: string
          updated_at?: string
          user_id?: string
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
