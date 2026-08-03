import sys

def modify_main():
    file_path = r'c:\Users\PC\Desktop\akkauntim-connect\bot\main.py'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the start block
    start_marker = "        min_conf = adj.get(\"min_confluence_score\", 20)"
    end_marker = "            logger.error(f\"❌ [{symbol}] Order xatolik: {order_msg}\")"

    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("Start marker topilmadi.")
        return
        
    end_idx = content.find(end_marker, start_idx)
    if end_idx == -1:
        print("End marker topilmadi.")
        return
        
    end_idx += len(end_marker)

    new_block = """        # ============================================================
        # AI AGENT AUTONOMOUS DECISION
        # ============================================================
        
        context = self.prompt_builder.build_context_summary(
            smc_result=smc_result or smc_context,
            patterns=pattern_result,
            news=news_result,
            voting={},
            memory_bank=memory_bank_text,
            wyckoff=wyckoff_result,
            sr_volume=sr_volume_result,
            auto_patterns=auto_patterns_result,
            kill_zones=kill_zones_result
        )
        context["pair"] = symbol
        context["timeframe"] = self.config.timeframe_major
        context["current_price"] = current_price

        prompt = self.prompt_builder.build_trading_prompt(context, symbol, current_price)
        logger.info(f"[{symbol}] AI Agent ga bozor tahlili yuborilmoqda...")
        
        ai_decision = self.ai.get_decision(prompt)
        if not ai_decision:
            logger.error(f"[{symbol}] AI javob bermadi — savdo bekor qilindi.")
            return

        final_decision = ai_decision.get("decision", "HOLD")
        logger.info(f"[{symbol}] AI Xulosasi: {final_decision} | Sabab: {ai_decision.get('reasoning', '')[:200]}")

        if final_decision == "HOLD":
            return
            
        pip_divisor = 0.1 if ("XAU" in symbol or "GOLD" in symbol) else (0.01 if "JPY" in symbol else 0.0001)
        
        entry_price = ai_decision.get("entry_price")
        if entry_price is None:
            entry_price = current_price
        
        sl_price = ai_decision.get("stop_loss")
        tp_price = ai_decision.get("take_profit")
        
        sl_pips = abs(entry_price - sl_price) / pip_divisor if sl_price else 50
        tp_pips = abs(entry_price - tp_price) / pip_divisor if tp_price else 100
        risk_pct = ai_decision.get("risk_pct", 0.01)

        # Signalni "BUY", "SELL", "BUY_LIMIT", "SELL_LIMIT" ga aylantirish
        if final_decision in ["BUY", "SELL"]:
            order_signal = final_decision
        elif final_decision == "LIMIT_BUY":
            order_signal = "BUY_LIMIT"
        elif final_decision == "LIMIT_SELL":
            order_signal = "SELL_LIMIT"
        else:
            order_signal = "BUY" # default fallback
            
        approved, msg, lot = self.risk.validate_trade(
            symbol=symbol,
            signal=order_signal if "LIMIT" not in order_signal else order_signal.split("_")[0],
            confidence=80, # AI o'zi qaror qilyapti
            stop_loss_pips=sl_pips,
            risk_pct=risk_pct
        )
        
        logger.info(f"[{symbol}] Risk natijasi: {msg} (Lot: {lot})")
        if not approved or lot is None:
            logger.info(f"[{symbol}] Risk manager rad etdi: {msg}")
            return
            
        # Log to db
        self.decision_logger.log(
            pair=symbol, timeframe=self.config.timeframe_major,
            context=context, prompt="AUTONOMOUS_AI",
            response=ai_decision, decision=final_decision,
            risk_pct=risk_pct, hash_val=self._get_state_hash(context),
            tokens={"input_tokens": self.ai.total_tokens_in, "output_tokens": self.ai.total_tokens_out},
            cost=self.ai.total_cost
        )

        try:
            self.sync.log_ai_signal(
                symbol=symbol, signal=final_decision, confidence=80, reasoning=ai_decision.get("reasoning", "")
            )
            self.sync.log_claude_cost(self.ai.total_cost)
        except Exception as e:
            logger.warning(f"Supabase sync xatolik: {e}")

        # Buyurtmani yuborish
        if "LIMIT" in order_signal:
            success, order_msg, order_info = self.orders.place_pending_order(
                symbol=symbol,
                order_type_str=order_signal,
                price=entry_price,
                lot_size=lot,
                stop_loss_pips=sl_pips,
                take_profit_pips=tp_pips,
                magic=self.config.magic_number,
                comment="AI Limit"
            )
        else:
            success, order_msg, order_info = self.orders.place_order(
                symbol=symbol,
                signal=order_signal,
                lot_size=lot,
                stop_loss_pips=sl_pips,
                take_profit_pips=tp_pips,
                entry_price=entry_price
            )

        if success:
            logger.info(
                f"✅ [{symbol}] AI Order ochildi! Ticket: {order_info.get('ticket', 'N/A')} | "
                f"Signal: {order_signal} | SL: {sl_pips:.1f} pip | TP: {tp_pips:.1f} pip | "
                f"Risk: {risk_pct:.1%}"
            )
            self.telegram.send_signal(
                symbol=symbol,
                signal=order_signal,
                confidence=80,
                sl=sl_pips,
                tp=tp_pips,
                reasoning=ai_decision.get("reasoning", "")
            )
        else:
            logger.error(f"❌ [{symbol}] Order xatolik: {order_msg}")"""

    new_content = content[:start_idx] + new_block + content[end_idx:]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("main.py muvaffaqiyatli tahrirlandi.")

if __name__ == "__main__":
    modify_main()
