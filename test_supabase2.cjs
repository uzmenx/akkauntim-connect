const { createClient } = require('@supabase/supabase-js');
const url = process.env.VITE_SUPABASE_URL;
const key = process.env.VITE_SUPABASE_PUBLISHABLE_KEY;
const supabase = createClient(url, key);

async function check() {
  const { data, error } = await supabase
    .from('bot_settings')
    .select('*')
    .limit(10);
    
  if (error) console.error("Error:", error);
  else {
      console.log("Settings:");
      console.log(data);
  }
}
check();
