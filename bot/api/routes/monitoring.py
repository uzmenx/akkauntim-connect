from fastapi import APIRouter, Query
from typing import Optional
import logging

from bot.engine.monitoring_engine import SystemMonitoringEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

monitoring_engine = SystemMonitoringEngine()

@router.get("/status")
async def get_system_status(symbol: str = Query("EURUSD", description="Monitoring uchun valyuta juftligi")):
    """
    Tizimning barcha 4 ta signal komponentlari (Voting, LSTM, PPO, Merger)
    real-time holati, anomaliyalar va xulosa hisobotini qaytaradi.
    """
    try:
        report = monitoring_engine.get_full_telemetry_report(symbol=symbol)
        return report
    except Exception as e:
        logger.error(f"Monitoring status olishda xatolik: {e}")
        return {
            "status": "ERROR",
            "message": str(e),
            "symbol": symbol
        }

@router.get("/component/{component_name}")
async def get_component_telemetry(component_name: str, symbol: str = Query("EURUSD")):
    """
    Muayyan komponent telemetry ma'lumotlarini beradi (voting, lstm, ppo, merger).
    """
    c_lower = component_name.lower()
    try:
        if "voting" in c_lower:
            return monitoring_engine.get_voting_engine_telemetry(symbol)
        elif "lstm" in c_lower:
            return monitoring_engine.get_lstm_engine_telemetry(symbol)
        elif "ppo" in c_lower or "rl" in c_lower:
            return monitoring_engine.get_ppo_agent_telemetry(symbol)
        elif "merger" in c_lower:
            return monitoring_engine.get_signal_merger_telemetry(symbol)
        else:
            return {"error": f"Noma'lum komponent: {component_name}"}
    except Exception as e:
        logger.error(f"Komponent telemetry xatosi ({component_name}): {e}")
        return {"error": str(e)}

@router.get("/anomalies")
async def get_active_anomalies(symbol: str = Query("EURUSD")):
    """
    Anomaliyalar, xatolar va veto holatlarini qaytaradi.
    """
    try:
        return monitoring_engine.detect_anomalies(symbol)
    except Exception as e:
        return [{"id": "ERR_01", "severity": "ERROR", "message": str(e)}]

@router.get("/drift")
async def get_model_drift(symbol: str = Query("EURUSD")):
    """
    Model drift nazorati va rolling win rate pasayish indikatorlarini qaytaradi.
    """
    try:
        return monitoring_engine.detect_model_drift(symbol)
    except Exception as e:
        logger.error(f"Model drift error: {e}")
        return {"error": str(e)}

@router.get("/train-comparison")
async def get_train_version_comparison(symbol: str = Query("EURUSD")):
    """
    Har bir train siklidan keyingi model versiya solishtirma (Model Version Delta) hisobotini beradi.
    """
    try:
        return monitoring_engine.generate_train_version_comparison_report(symbol)
    except Exception as e:
        logger.error(f"Train comparison report error: {e}")
        return {"error": str(e)}

@router.get("/error-aggregation")
async def get_centralized_error_aggregation():
    """
    Markazlashtirilgan xatolar (MT5 disconnect, LLM API timeout, DB lock) chastotasi va hisobotini beradi.
    """
    try:
        return monitoring_engine.get_centralized_error_aggregation_report()
    except Exception as e:
        logger.error(f"Error aggregation report error: {e}")
        return {"error": str(e)}

@router.get("/health-report")
async def get_system_health_report(
    period: str = Query("WEEKLY", description="WEEKLY, MONTHLY"),
    symbol: str = Query("EURUSD")
):
    """
    Har haftalik/oylik avtomatik salomatlik hisoboti (Health Report).
    """
    try:
        return monitoring_engine.generate_system_health_report(period=period, symbol=symbol)
    except Exception as e:
        logger.error(f"System health report error: {e}")
        return {"error": str(e)}

@router.post("/trigger-telegram-drift-alert")
async def trigger_telegram_drift_alert(symbol: str = Query("EURUSD")):
    """
    Model drift holatida Telegram ga fallback ogohlantirish yuborishni sinab ko'radi.
    """
    try:
        drift_data = monitoring_engine.detect_model_drift(symbol)
        from bot.config import config
        from bot.sync.telegram_sync import TelegramSync
        tg = TelegramSync(config)
        tg.send_model_drift_alert(symbol, drift_data)
        return {"status": "SUCCESS", "message": "Telegram model drift alert triggers fired", "drift": drift_data}
    except Exception as e:
        logger.error(f"Telegram alert trigger error: {e}")
        return {"status": "ERROR", "error": str(e)}



@router.get("/ab-test-shadow")
async def get_ab_test_shadow_report(symbol: str = Query("EURUSD")):
    """
    A/B test parallel shadow monitoring (Model A vs Model B) report.
    """
    try:
        return monitoring_engine.get_ab_test_shadow_engine_report(symbol)
    except Exception as e:
        logger.error(f"A/B test shadow report error: {e}")
        return {"error": str(e)}

@router.get("/audit-why-chain")
async def get_decision_why_chain_audit(
    symbol: str = Query("EURUSD"),
    decision_id: Optional[str] = Query(None, description="Optional specific decision ID")
):
    """
    "Qora quti bo'lmaslik" (Anti-Blackbox) audit endpoint:
    Har bir yakuniy qarorning qaysi modul, qanday og'irlik, qaysi feature va qanday matematika
    bilan qabul qilinganining to'liq "NEGA" (WHY Chain) izohini beradi.
    """
    try:
        return monitoring_engine.get_decision_why_chain_audit(symbol=symbol, decision_id=decision_id)
    except Exception as e:
        logger.error(f"Audit WHY chain endpoint error: {e}")
        return {"error": str(e)}

@router.get("/logs")
async def get_diagnostic_logs(
    limit: int = Query(30, ge=1, le=200),
    level: Optional[str] = Query("ALL", description="INFO, WARN, ERROR, VETO, ANOMALY"),
    component: Optional[str] = Query("ALL", description="Voting, LSTM, PPO, Merger, ALL")
):
    """
    Tizim komponentlarining diagnostika va ijro loglarini filtrlangan ko'rinishda beradi.
    """
    try:
        logs = monitoring_engine.get_diagnostic_logs(limit=limit, level_filter=level, component_filter=component)
        return {
            "total_count": len(logs),
            "level_filter": level,
            "component_filter": component,
            "logs": logs
        }
    except Exception as e:
        logger.error(f"Diagnostic logs error: {e}")
        return {"total_count": 0, "logs": [], "error": str(e)}
