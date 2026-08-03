const fs = require('fs');
let code = fs.readFileSync('src/components/TradingChartModal.tsx', 'utf8');

const targetStr = `  useEffect(() => {
    if (!isOpen || !activeSymbol) return;

    let isMounted = true;
    const fetchChartData = async () => {`;

const newCode = `  useEffect(() => {
    if (!isOpen || !activeSymbol) return;

    let isMounted = true;
    const fetchChartData = async () => {
      setIsLoading(true);
      setError(null);
      setIsEmpty(false);

      const cacheKey = \`chartData_\${activeSymbol}_\${timeframe}\`;
      
      try {
        // Try to load cached data for offline support
        const cached = await get(cacheKey).catch(() => null);
        if (cached && isMounted) {
          if (cached.candles && cached.candles.length > 0) setCandlesData(cached.candles);
          if (cached.smc && showSMC) setSmcZonesData(cached.smc);
          if (cached.harmonic && showHarmonic) setHarmonicData(cached.harmonic);
          if (cached.wyckoff && showWyckoff) setWyckoffData(cached.wyckoff);
          if (cached.srVolume && showSRVolume) setSrVolumeData(cached.srVolume);
          if (cached.autoPattern && showAutoPattern) setAutoPatternData(cached.autoPattern);
          
          if (cached.candles && cached.candles.length > 0) {
             setIsLoading(false); // Stop loading early if we have cache
          }
        }
        
        let newSmc = showSMC ? [] : cached?.smc || [];
        let newHarmonic = showHarmonic ? [] : cached?.harmonic || [];
        let newWyckoff = showWyckoff ? [] : cached?.wyckoff || [];
        let newSrVolume = showSRVolume ? [] : cached?.srVolume || [];
        let newAutoPattern = showAutoPattern ? [] : cached?.autoPattern || [];

        // Fetch fresh candles
        const { data: candles, error: candlesError } = await supabase
          .from("candles")
          .select("*")
          .eq("symbol", activeSymbol)
          .eq("timeframe", timeframe)
          .order("time", { ascending: false })
          .limit(300);

        if (candlesError) throw candlesError;

        if (!candles || candles.length === 0) {
          if (isMounted && !cached?.candles?.length) setIsEmpty(true);
          return;
        }

        const formattedCandles = candles.reverse().map((c: any) => ({
          time: Math.floor(new Date(c.time).getTime() / 1000),
          open: Number(c.open),
          high: Number(c.high),
          low: Number(c.low),
          close: Number(c.close),
          volume: c.volume ? Number(c.volume) : 0,
        }));

        if (isMounted) setCandlesData(formattedCandles);

        if (showSMC) {
          const { data: zones } = await supabase.from("smc_zones").select("*").eq("symbol", activeSymbol).eq("timeframe", timeframe).eq("status", "fresh");
          if (zones) { newSmc = zones; if (isMounted) setSmcZonesData(zones); }
        }

        if (showHarmonic) {
          const { data: harmonics } = await (supabase as any).from("harmonic_patterns").select("*").eq("symbol", activeSymbol).eq("timeframe", timeframe).eq("status", "fresh");
          if (harmonics) { newHarmonic = harmonics; if (isMounted) setHarmonicData(harmonics); }
        }

        if (showWyckoff) {
          const { data: wyckoffs } = await (supabase as any).from("wyckoff_events").select("*").eq("symbol", activeSymbol).eq("timeframe", timeframe).eq("status", "fresh");
          if (wyckoffs) { newWyckoff = wyckoffs; if (isMounted) setWyckoffData(wyckoffs); }
        }

        if (showSRVolume) {
          const { data: sr } = await (supabase as any).from("sr_volume_zones").select("*").eq("symbol", activeSymbol).eq("timeframe", timeframe).eq("status", "fresh");
          if (sr) { newSrVolume = sr; if (isMounted) setSrVolumeData(sr); }
        }

        if (showAutoPattern) {
          const { data: ap } = await (supabase as any).from("auto_patterns").select("*").eq("symbol", activeSymbol).eq("timeframe", timeframe).eq("status", "fresh");
          if (ap) { newAutoPattern = ap; if (isMounted) setAutoPatternData(ap); }
        }
        
        // Cache the fresh data
        await set(cacheKey, {
          candles: formattedCandles,
          smc: newSmc,
          harmonic: newHarmonic,
          wyckoff: newWyckoff,
          srVolume: newSrVolume,
          autoPattern: newAutoPattern
        }).catch(() => null);

      } catch (err: any) {
        // If we have cached data, silently fail
        const cached = await get(cacheKey).catch(() => null);
        if (!cached?.candles?.length && isMounted) {
           setError(err.message || "Ma'lumotlarni yuklashda xatolik yuz berdi");
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };`;

const endTarget = `      } catch (err: any) {
        if (isMounted) setError(err.message || "Ma'lumotlarni yuklashda xatolik yuz berdi");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };`;

let startIndex = code.indexOf(targetStr);
let endIndex = code.indexOf(endTarget);

if (startIndex > -1 && endIndex > -1) {
    code = code.substring(0, startIndex) + newCode + code.substring(endIndex + endTarget.length);
    fs.writeFileSync('src/components/TradingChartModal.tsx', code);
    console.log("Successfully replaced");
} else {
    console.log("Target not found!");
}
