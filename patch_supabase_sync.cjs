const fs = require('fs');
let code = fs.readFileSync('bot/sync/supabase_sync.py', 'utf8');

const targetStr = `        import threading
        def _do_post():`;

const newCode = `        import threading
        def _do_post():
            # POST strategy overlays directly using REST API
            try:
                import requests
                headers = {
                    "apikey": self.config.supabase_key,
                    "Authorization": f"Bearer {self.config.supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates"
                }
                
                # Fetch user_id using mt5_login
                user_res = requests.get(
                    f"{self.config.supabase_url}/rest/v1/users?mt5_login=eq.{self.mt5_login}&select=id",
                    headers=headers
                )
                if user_res.status_code < 300 and user_res.json():
                    user_id = user_res.json()[0]['id']
                    
                    if strategy_overlays:
                        tables = {
                            "smc": "smc_zones",
                            "harmonic": "harmonic_patterns",
                            "wyckoff": "wyckoff_events",
                            "sr_volume": "sr_volume_zones",
                            "auto_patterns": "auto_patterns"
                        }
                        
                        for key, table in tables.items():
                            items = strategy_overlays.get(key, [])
                            if items:
                                # First, delete fresh ones for this symbol/tf
                                requests.delete(
                                    f"{self.config.supabase_url}/rest/v1/{table}?symbol=eq.{symbol}&timeframe=eq.{timeframe}&status=eq.fresh&user_id=eq.{user_id}",
                                    headers=headers
                                )
                                # Then insert new ones
                                for item in items:
                                    item['user_id'] = user_id
                                requests.post(
                                    f"{self.config.supabase_url}/rest/v1/{table}",
                                    headers=headers,
                                    json=items
                                )
                                
            except Exception as e:
                logger.debug(f"Direct REST strategy sync error: {e}")
`;

let startIndex = code.indexOf(targetStr);
if (startIndex > -1) {
    code = code.substring(0, startIndex) + newCode + code.substring(startIndex);
    fs.writeFileSync('bot/sync/supabase_sync.py', code);
    console.log("Successfully replaced");
} else {
    console.log("Target not found!");
}
