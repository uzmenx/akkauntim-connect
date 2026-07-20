import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";

const TABLES = ["bot_status", "positions", "trade_history", "ai_signals", "bot_settings"] as const;

/**
 * Subscribe to realtime changes on all bot-related tables and
 * invalidate every react-query cache entry so the UI refreshes instantly.
 */
export function useRealtimeSync(enabled: boolean) {
  const qc = useQueryClient();

  useEffect(() => {
    if (!enabled) return;

    const channel = supabase.channel("bot-realtime");

    TABLES.forEach((table) => {
      channel.on(
        // @ts-expect-error - postgres_changes is a valid event type
        "postgres_changes",
        { event: "*", schema: "public", table },
        () => {
          qc.invalidateQueries({ queryKey: [table] });
          // also invalidate legacy keys used across pages
          if (table === "positions") {
            qc.invalidateQueries({ queryKey: ["positions"] });
            qc.invalidateQueries({ queryKey: ["positions_full"] });
          }
          if (table === "trade_history") {
            qc.invalidateQueries({ queryKey: ["trade_history"] });
            qc.invalidateQueries({ queryKey: ["history_today"] });
          }
          if (table === "bot_status") {
            qc.invalidateQueries({ queryKey: ["bot_status"] });
          }
          if (table === "ai_signals") {
            qc.invalidateQueries({ queryKey: ["ai_signals"] });
          }
          if (table === "bot_settings") {
            qc.invalidateQueries({ queryKey: ["bot_settings"] });
          }
        },
      );
    });

    channel.subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [enabled, qc]);
}
