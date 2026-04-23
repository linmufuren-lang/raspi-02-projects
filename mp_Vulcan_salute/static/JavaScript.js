var socket = io();
const messageOverlay = document.getElementById('message-overlay');
const detectFlash = document.getElementById('detect-flash');
const countEl = document.getElementById('count');
const startOverlay = document.getElementById('start-overlay');
const startBtn = document.getElementById('start-btn');
let detectCount = 0;

// スタートボタン押下でブラウザの自動再生ポリシーを解除
startBtn.addEventListener('click', function() {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    ctx.close();
    startOverlay.style.display = 'none';
});

function playAudio(filename) {
    const audio = new Audio('/static/' + filename + '?t=' + Date.now());
    audio.play().catch(e => console.error("Play error:", e));
}

socket.on('vulcan_detected', function() {
    detectCount++;
    countEl.textContent = detectCount;

    detectFlash.textContent = '🖖 Vulcan Detected!';
    detectFlash.style.backgroundColor = '#00ffcc';
    detectFlash.style.color = '#000';
    detectFlash.style.display = 'block';
    messageOverlay.textContent = 'Live long and prosper';
    messageOverlay.style.display = 'block';

    playAudio('vulcan.mp3');

    setTimeout(() => {
        detectFlash.style.display = 'none';
        messageOverlay.style.display = 'none';
    }, 3500);
});

socket.on('vulcan_climax', function() {
    detectCount = 0;
    countEl.textContent = detectCount;

    detectFlash.textContent = '🖖🖖🖖 5回達成！クライマックス！🖖🖖🖖';
    detectFlash.style.backgroundColor = '#ff6600';
    detectFlash.style.color = '#fff';
    detectFlash.style.display = 'block';
    messageOverlay.textContent = '🖖🖖 長寿と繁栄を 🖖🖖';
    messageOverlay.style.display = 'block';

    playAudio('startrek.mp3');

    setTimeout(() => {
        detectFlash.style.display = 'none';
        messageOverlay.style.display = 'none';
    }, 6000);
});
