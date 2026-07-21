"""
test_smc_live.py
================
MT5 dan real tarixiy data olib smc_engine.py ni sinash.

Ishga tushirish:
  cd c:\\Users\\PC\\Desktop\\akkauntim-connect
  python test_smc_live.py

Natijani konsolda chiroyli formatda chiqaradi:
  - Joriy trend
  - Oxirgi BoS/ChoCh
  - Oxirgi 5 ta Order Block
  - FVG ro'yxati
  - Likvidlik darajalari
"""

import sys
import json

# Windows cp1251 encoding fix
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    import MetaTrader5 as mt5
except ImportError:
    print("⚠️  MetaTrader5 kutubxonasi topilmadi.")
    print("   pip install MetaTrader5")
    print("   yoki MT5 o'rnatilingan kompyuterda ishga tushiring.")
    sys.exit(1)

import pandas as pd
from smc_engine import analyze_market_structure


def get_mt5_data(symbol: str, timeframe, bars: int = 500) -> pd.DataFrame:
    """MT5 dan OHLC data olish."""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"{symbol} uchun data olib bo'lmadi: {mt5.last_error()}")

    df = pd.DataFrame(rates)
    df["timestamp"] = pd.to_datetime(df["time"], unit="s")
    df = df.rename(columns={
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
    })
    return df[["timestamp", "open", "high", "low", "close", "tick_volume"]].rename(
        columns={"tick_volume": "volume"}
    )


def print_header(text: str):
    """Chiroyli sarlavha."""
    print(f"\n{'━' * 60}")
    print(f"  {text}")
    print(f"{'━' * 60}")


def print_section(title: str):
    """Bo'lim sarlavhasi."""
    print(f"\n  ╔{'═' * 54}╗")
    print(f"  ║  {title:<52}║")
    print(f"  ╚{'═' * 54}╝")


def format_price(price, decimals=5):
    """Narxni formatlash."""
    if price is None:
        return "N/A"
    return f"{price:.{decimals}f}"


def main():
    # ===== MT5 ulanish =====
    if not mt5.initialize():
        print(f"❌ MT5 ulanishda xatolik: {mt5.last_error()}")
        sys.exit(1)

    print_header("🔍 SMC Engine — Real Data Test")
    print(f"  MT5 versiya: {mt5.version()}")

    symbols = ["EURUSD", "GBPUSD", "XAUUSD"]
    timeframes = {
        "H1": mt5.TIMEFRAME_H1,
        "M15": mt5.TIMEFRAME_M15,
    }

    for symbol in symbols:
        for tf_name, tf_value in timeframes.items():
            try:
                print_header(f"📊 {symbol} — {tf_name}")

                # Data olish
                df = get_mt5_data(symbol, tf_value, bars=500)
                print(f"  📈 Data: {len(df)} bar, {df['timestamp'].iloc[0]} → {df['timestamp'].iloc[-1]}")

                # SMC tahlili
                config = {
                    "pivot_period": 5,
                    "ob_validity_bars": 300,
                    "ob_refine": True,
                    "ob_refine_method": "Defensive",
                    "fvg_filter": True,
                    "fvg_filter_type": "Defensive",
                    "static_pivot_period": 8,
                    "dynamic_pivot_period": 3,
                }

                result = analyze_market_structure(df, config)

                # ===== 1. Trend =====
                print_section("📍 TREND")
                ext = result["trend"]["external"]
                int_ = result["trend"]["internal"]
                ext_emoji = "🟢" if ext == "Up Trend" else "🔴" if ext == "Down Trend" else "⚪"
                int_emoji = "🟢" if int_ == "Up Trend" else "🔴" if int_ == "Down Trend" else "⚪"
                print(f"    Tashqi (Major): {ext_emoji} {ext}")
                print(f"    Ichki (Minor):  {int_emoji} {int_}")
                print(f"    Joriy narx:     {format_price(result['current_price'])}")

                # ===== 2. Oxirgi BoS / ChoCh =====
                print_section("⚡ OXIRGI BoS / ChoCh")

                bos = result["last_bos"]
                if bos:
                    bos_emoji = "🟢" if bos["type"] == "Bullish" else "🔴"
                    print(f"    BoS:   {bos_emoji} {bos['type']} {bos['level']} @ {format_price(bos['price'])} (bar #{bos['bar_index']})")
                else:
                    print("    BoS:   ⚪ Topilmadi")

                choch = result["last_choch"]
                if choch:
                    choch_emoji = "🟢" if choch["type"] == "Bullish" else "🔴"
                    print(f"    ChoCh: {choch_emoji} {choch['type']} {choch['level']} @ {format_price(choch['price'])} (bar #{choch['bar_index']})")
                else:
                    print("    ChoCh: ⚪ Topilmadi")

                # ===== 3. Order Blocks (oxirgi 5 ta) =====
                print_section("📦 ORDER BLOCKS (oxirgi 5 ta)")

                all_obs = result["order_blocks"]["demand"] + result["order_blocks"]["supply"]
                # bar_index bo'yicha tartiblash (eng yangilari birinchi)
                all_obs.sort(key=lambda x: x["bar_index"], reverse=True)

                if all_obs:
                    for i, ob in enumerate(all_obs[:5]):
                        ob_type = "🟩 Demand" if ob in result["order_blocks"]["demand"] else "🟥 Supply"
                        status = "🔵 Fresh" if ob["status"] == "fresh" else "⚫ Mitigated"
                        print(f"    {i+1}. {ob_type} | {ob['origin']:<12} | {ob['level']:<6}")
                        print(f"       Zone: {format_price(ob['bottom'])} → {format_price(ob['top'])} | {status}")
                        print(f"       Bar: #{ob['bar_index']} | Distance: {ob['distance_pct']:.2f}%")
                else:
                    print("    ⚪ OB topilmadi")

                fresh_obs = [ob for ob in all_obs if ob["status"] == "fresh"]
                print(f"\n    Jami: {len(all_obs)} OB ({len(fresh_obs)} fresh)")

                # ===== 4. FVG =====
                print_section("📐 FVG (Fair Value Gaps)")

                demand_fvgs = [f for f in result["fvg"]["demand"] if f["status"] == "fresh"]
                supply_fvgs = [f for f in result["fvg"]["supply"] if f["status"] == "fresh"]

                print(f"    Demand FVG (fresh): {len(demand_fvgs)}")
                for fvg in demand_fvgs[-3:]:
                    print(f"      🟩 {format_price(fvg['bottom'])} → {format_price(fvg['top'])} (gap: {format_price(fvg['gap_size'])})")

                print(f"    Supply FVG (fresh): {len(supply_fvgs)}")
                for fvg in supply_fvgs[-3:]:
                    print(f"      🟥 {format_price(fvg['bottom'])} → {format_price(fvg['top'])} (gap: {format_price(fvg['gap_size'])})")

                total_fvgs = len(result["fvg"]["demand"]) + len(result["fvg"]["supply"])
                print(f"    Jami: {total_fvgs} FVG ({len(demand_fvgs) + len(supply_fvgs)} fresh)")

                # ===== 5. Liquidity =====
                print_section("💧 LIQUIDITY DARAJALARI")

                liq = result["liquidity"]
                print(f"    Statik High:  {format_price(liq['static_high'])}")
                print(f"    Statik Low:   {format_price(liq['static_low'])}")
                print(f"    Dinamik High: {format_price(liq['dynamic_high'])}")
                print(f"    Dinamik Low:  {format_price(liq['dynamic_low'])}")

                # ===== 6. Xulosa =====
                print_section("📊 XULOSA")
                s = result["summary"]
                print(f"    Jami hodisalar:   {s['total_events']}")
                print(f"    Jami OB:          {s['total_obs']} ({s['fresh_obs']} fresh)")
                print(f"    Jami FVG:         {s['total_fvgs']} ({s['fresh_fvgs']} fresh)")

            except Exception as e:
                print(f"  ❌ Xatolik: {e}")
                import traceback
                traceback.print_exc()

            print()

    # ===== JSON output (debug uchun) =====
    try:
        df = get_mt5_data("EURUSD", mt5.TIMEFRAME_H1, bars=200)
        result = analyze_market_structure(df)
        print_header("📋 JSON Output (EURUSD H1)")
        # Faqat summary va trend chiqaramiz (to'liq JSON juda katta)
        compact = {
            "current_price": result["current_price"],
            "trend": result["trend"],
            "last_bos": result["last_bos"],
            "last_choch": result["last_choch"],
            "summary": result["summary"],
            "demand_obs_count": len(result["order_blocks"]["demand"]),
            "supply_obs_count": len(result["order_blocks"]["supply"]),
        }
        print(json.dumps(compact, indent=2, default=str))
    except Exception as e:
        print(f"  ❌ JSON output xatolik: {e}")

    mt5.shutdown()
    print_header("✅ Test tugadi")


if __name__ == "__main__":
    main()
