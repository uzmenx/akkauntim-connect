module.exports = {
  apps: [{
    name: 'yuksalish-bot',
    script: 'run_bot.py',
    interpreter: 'python',
    watch: false,
    autorestart: true,
    max_restarts: 10,
    restart_delay: 5000,
    env: {
      NODE_ENV: 'production'
    },
    // Kill switch or graceful reload timeout
    kill_timeout: 3000,
  }]
};
