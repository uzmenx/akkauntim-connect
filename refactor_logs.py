import os
import re

def refactor_monitoring_engine_logs():
    with open("bot/engine/monitoring_engine.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Refactor get_diagnostic_logs
    logs_replacement = """
    def get_diagnostic_logs(self, limit: int = 30, level_filter: Optional[str] = None, component_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        \"\"\"So'nggi tizim va komponent ijro loglarini olish.\"\"\"
        logs = []
        try:
            if os.path.exists(self.decisions_db):
                conn = sqlite3.connect(self.decisions_db, timeout=5)
                c = conn.cursor()
                c.execute(
                    "SELECT timestamp, pair, timeframe, final_decision, risk_pct, context_json, ai_response FROM ai_decisions ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
                rows = c.fetchall()
                conn.close()
                for r in rows:
                    logs.append({
                        "timestamp": r[0],
                        "symbol": r[1],
                        "timeframe": r[2],
                        "level": "INFO" if r[3] in ["BUY", "SELL"] else "WARN",
                        "component": "Signal Merger",
                        "event": f"Signal Decision: {r[3]} (Risk: {r[4]}%)",
                        "details": {
                            "decision": r[3],
                            "risk_pct": r[4],
                            "raw_response": r[6][:100] if r[6] else ""
                        }
                    })
        except Exception as e:
            logger.warning(f"Diagnostic log read error: {e}")

        # Apply filters
        if level_filter and level_filter != "ALL":
            logs = [l for l in logs if l["level"] == level_filter]

        if component_filter and component_filter != "ALL":
            logs = [l for l in logs if component_filter.lower() in l.get("component", "").lower()]

        return logs
"""
    
    content = re.sub(r'    def get_diagnostic_logs\(self.*?return logs', logs_replacement.strip('\n'), content, flags=re.DOTALL)

    anomalies_replacement = """
    def detect_anomalies(self, symbol: str = "EURUSD") -> List[Dict[str, Any]]:
        \"\"\"Real-time anomaliya, xatolar va xavflarni aniqlaydi.\"\"\"
        anomalies = []

        # 1. Stuck / Constant Output Anomaly Check
        stuck_alerts = self.detect_stuck_output_anomalies(symbol)
        anomalies.extend(stuck_alerts)

        # 2. Model Concept Drift Warning
        drift_info = self.detect_model_drift(symbol)
        if drift_info["drift_status"] in ["MODERATE_DRIFT", "SEVERE_DRIFT"]:
            anomalies.append({
                "id": "ANOMALY_DRIFT_01",
                "severity": "WARNING" if drift_info["drift_status"] == "MODERATE_DRIFT" else "ERROR",
                "component": "LSTM & PPO Learning Core",
                "code": "MODEL_ACCURACY_DRIFT_DETECTED",
                "message": f"Model drift aniqlandi! Win rate {drift_info['baseline_win_rate_pct']}% dan {drift_info['recent_win_rate_pct']}% ga tushib ketdi (Farq: {drift_info['drift_delta_pct']}%).",
                "timestamp": datetime.now().isoformat(),
                "action": "Modelni yangi bozor ma'lumotlari bilan qayta train qiling (Trigger Incremental Retrain)."
            })

        # 3. Merger Veto / Disagreement Alert
        merger = self.get_signal_merger_telemetry(symbol)
        if merger.get("veto_triggered"):
            anomalies.append({
                "id": "ANOMALY_VETO_01",
                "severity": "WARNING",
                "component": "Signal Merger",
                "code": "STRONG_SIGNAL_DISAGREEMENT",
                "message": f"Voting va LSTM o'rtasida kuchli kelishmovchilik aniqlandi! Conflict weight = {merger.get('conflict_weight')}. Signal veto qilindi (NEUTRAL).",
                "timestamp": datetime.now().isoformat(),
                "action": "Signal avtomatik rad etildi. Boshqa timeframe'larni tahlil qiling."
            })

        # 4. Latency Check
        lstm = self.get_lstm_engine_telemetry(symbol)
        if lstm.get("latency_ms", 0) > 150:
            anomalies.append({
                "id": "ANOMALY_LATENCY_02",
                "severity": "WARNING",
                "component": "LSTM Predictor",
                "code": "HIGH_INFERENCE_LATENCY",
                "message": f"LSTM neyron tarmog'i javob berish vaqti normadan yuqori ({lstm.get('latency_ms')} ms > 150 ms).",
                "timestamp": datetime.now().isoformat(),
                "action": "Batch hajmini va PyTorch CUDA drayverini tekshiring."
            })

        return anomalies
"""

    content = re.sub(r'    def detect_anomalies\(self.*?return anomalies', anomalies_replacement.strip('\n'), content, flags=re.DOTALL)

    with open("bot/engine/monitoring_engine.py", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    refactor_monitoring_engine_logs()
