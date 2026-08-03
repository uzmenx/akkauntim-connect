const { createClient } = require('@supabase/supabase-js');
const url = process.env.VITE_SUPABASE_URL;
const key = process.env.VITE_SUPABASE_PUBLISHABLE_KEY;
const supabase = createClient(url, key);

async function check() {
  const { data, error } = await supabase
    .from('ai_signals')
    .select('*')
    .eq('symbol', 'SYSTEM')
    .order('created_at', { ascending: false })
    .limit(10);
    
  if (error) console.error("Error:", error);
  else {
      console.log("System Logs:");
      data.forEach(d => console.log(d.created_at, d.signal, d.reasoning));
  }
}
check();
