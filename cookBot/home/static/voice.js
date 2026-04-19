// Disclosure Claude helped Roman make this as there were a bunch of issues with JS and HTML interactions

// ─────────────────────────────────────────────────
// STATE variables to help track where we are at
// ─────────────────────────────────────────────────
var steps       = [];
var ingredients = [];
var current     = 0; // Keep track of current step
var stopped     = false; // Keeps track if user manually stops the listener
var cmdMode     = false; // Tells us if we activated command mode by saying "hey chef"
var cmdTimer    = null; // A timer for command mode
var recognizing = false; // Tells us if the API speek mode is on, which stops other commands
var recog       = null; // Holds the speech recognition object (aka what user said)

// ─────────────────────────────────────────────────
// LOAD DATA into the javascript so we can communicate made by Roman and Claude
// ─────────────────────────────────────────────────
(function loadData() {
  var s = document.getElementById('steps-data');
  var i = document.getElementById('ingredients-data');
  if (s) { try { steps       = JSON.parse(s.textContent); } catch(e) { console.error('[Chef] steps parse error:', e); } }
  if (i) { try { ingredients = JSON.parse(i.textContent); } catch(e) { console.error('[Chef] ing parse error:',   e); } }
  console.log('[Chef] Loaded', steps.length, 'steps,', ingredients.length, 'ingredients');
})();

// ─────────────────────────────────────────────────
// UI HELPERS to help diplay proper text made by Claude
// ─────────────────────────────────────────────────
// logic to update if we are listening/stopped/speaking
function setStatus(text, mode) {
  var s = document.getElementById('voiceStatus');
  var d = document.getElementById('voiceIndicator');
  if (s) s.innerText = text;
  if (d) { d.className = 'voice-indicator'; if (mode) d.classList.add(mode); }
}

// logic to display the text heard if wanted
function setHeard(text) {
  var el = document.getElementById('voiceHeard');
  if (el) el.innerText = text;
}

// logic to disable next/prev if at beginning or end of list
function updateNav() {
  var p = document.getElementById('prevBtn');
  var n = document.getElementById('nextBtn');
  if (p) p.disabled = (current === 0);
  if (n) n.disabled = (current === steps.length - 1);
}

// ─────────────────────────────────────────────────
// RENDER STEPS made by Claude and Roman
// ─────────────────────────────────────────────────
function renderSteps() {
  var list = document.getElementById('stepsList');
  if (!list) return;
  list.innerHTML = '';
  steps.forEach(function(step, idx) {
    var li = document.createElement('li');
    li.className = 'step-item';
    li.id = 'step-' + idx;

    var num = document.createElement('div');
    num.className = 'step-num';
    num.innerText = idx + 1;

    var body = document.createElement('div');
    body.className = 'step-body';

    var text = document.createElement('div');
    text.className = 'step-text';
    text.innerText = step;

    var acts = document.createElement('div');
    acts.className = 'step-actions';

    var readBtn = document.createElement('button');
    readBtn.className = 'step-btn read-btn';
    readBtn.innerText = '\uD83D\uDD0A Read aloud';
    readBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      goTo(idx);
      speak(step);
    });

    var doneBtn = document.createElement('button');
    doneBtn.className = 'step-btn';
    doneBtn.innerText = '\u2713 Done';
    doneBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      li.classList.toggle('done');
    });

    acts.appendChild(readBtn);
    acts.appendChild(doneBtn);
    body.appendChild(text);
    body.appendChild(acts);
    li.appendChild(num);
    li.appendChild(body);
    li.addEventListener('click', function() { goTo(idx); });
    list.appendChild(li);
  });
}

// ─────────────────────────────────────────────────
// STEP NAVIGATION made by Claude
// ─────────────────────────────────────────────────
function goTo(idx) {
  current = Math.max(0, Math.min(idx, steps.length - 1));
  document.querySelectorAll('.step-item').forEach(function(el, i) {
    el.classList.toggle('active', i === current);
  });
  var a = document.getElementById('step-' + current);
  if (a) a.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  updateNav();
}

// ─────────────────────────────────────────────────
// TTS made by Roman and Claude
// ─────────────────────────────────────────────────
function speak(text) {
  safeStop();
  setStatus('Speaking\u2026', 'speaking');
  setHeard('');
  var u = new SpeechSynthesisUtterance(text);
  u.lang = 'en-US';
  u.onend = function() {
    if (!stopped) {
      setTimeout(function() {
        setStatus('Listening\u2026 say \u201CHey Chef\u201D', 'listening');
        safeStart();
      }, 400);
    } else {
      setStatus('Stopped', '');
    }
  };
  u.onerror = function() {
    if (!stopped) setTimeout(safeStart, 400);
  };
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
}

// ─────────────────────────────────────────────────
// BEEP (Web Audio) Made bt Claude
// ─────────────────────────────────────────────────
// logic to control the beep that plays when we say "hey chef"
function beep() {
  try {
    var ctx = new (window.AudioContext || window.webkitAudioContext)();
    var o = ctx.createOscillator();
    var g = ctx.createGain();
    o.connect(g); g.connect(ctx.destination);
    o.frequency.value = 880;
    g.gain.setValueAtTime(0.25, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
    o.start(ctx.currentTime); o.stop(ctx.currentTime + 0.2);
  } catch(e) {}
}

// ─────────────────────────────────────────────────
// COMMAND PARSING made by Roman and Claude
// ─────────────────────────────────────────────────
var wordNums = { one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9,ten:10,eleven:11,twelve:12 };

function extractNum(t) {
  var d = t.match(/\b(\d+)\b/);
  if (d) return parseInt(d[1], 10);
  var ws = t.split(/\s+/);
  for (var i = 0; i < ws.length; i++) { if (wordNums[ws[i]]) return wordNums[ws[i]]; }
  return null;
}

function handleCmd(t) {
  console.log('[Chef] command:', t);

  if (/\b(start|beginning|restart|first)\b/.test(t)) {
    if (steps.length === 0) { speak("This recipe has no steps."); return; }
    goTo(0); speak('Starting from the beginning. Step 1. ' + steps[0]);
    return;
  }

  if (/\b(next|forward|continue)\b/.test(t)) {
    if (current < steps.length - 1) { goTo(current + 1); speak('Step ' + (current + 1) + '. ' + steps[current]); }
    else speak("That's the last step \u2014 you're done!");
    return;
  }
  if (/\b(previous|back|before|last)\b/.test(t)) {
    if (current > 0) { goTo(current - 1); speak('Step ' + (current + 1) + '. ' + steps[current]); }
    else speak("You're already on the first step.");
    return;
  }
  if (/\b(repeat|again|current)\b/.test(t)) {
    speak('Step ' + (current + 1) + '. ' + steps[current]);
    return;
  }
  if (/\b(read|go to|step)\b/.test(t)) {
    var n = extractNum(t);
    if (n !== null && n >= 1 && n <= steps.length) { goTo(n - 1); speak('Step ' + n + '. ' + steps[current]); }
    else if (n !== null) speak('There is no step ' + n + '.');
    else speak('Step ' + (current + 1) + '. ' + steps[current]);
    return;
  }
  if (/\b(ingredient|ingredients|what do i need)\b/.test(t)) {
    speak(ingredients.length ? 'Ingredients: ' + ingredients.join('. ') : 'No ingredients listed.');
    return;
  }
  if (/\b(start|beginning|restart|first)\b/.test(t)) {
    goTo(0); speak('Starting from the beginning. Step 1. ' + steps[0]);
    return;
  }
  speak("Sorry, I didn't catch that.");
}

// ─────────────────────────────────────────────────
// SPEECH RECOGNITION made bt Roman and Claude
// ─────────────────────────────────────────────────
function safeStart() {
  if (!recog || recognizing || speechSynthesis.speaking) return;
  try { recog.start(); } catch(e) { console.warn('[Chef] start():', e.message); }
}

function safeStop() {
  if (!recog) return;
  try { recog.stop(); } catch(e) {}
}

function setupRecog() {
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    setStatus('Voice not supported \u2014 try Chrome or Edge', '');
    return;
  }

  recog = new SR();
  recog.continuous      = true;
  recog.interimResults  = false;
  recog.lang            = 'en-US';
  recog.maxAlternatives = 1;

  recog.onstart = function() { recognizing = true; };

  recog.onend = function() {
    recognizing = false;
    if (!stopped && !speechSynthesis.speaking) setTimeout(safeStart, 250);
  };

  recog.onerror = function(e) {
    recognizing = false;
    console.warn('[Chef] error:', e.error);
    if (e.error === 'not-allowed') {
      setStatus('Microphone blocked \u2014 check browser permissions', '');
      stopped = true;
      return;
    }
    if (!stopped && !speechSynthesis.speaking) setTimeout(safeStart, 300);
  };

  recog.onresult = function(event) {
    var r = event.results[event.results.length - 1];
    var t = r[0].transcript.toLowerCase().trim();
    console.log('[Chef] heard:', t);
    setHeard('\u201C' + t + '\u201D');

    if (/hey\s*chef/.test(t)) {
      cmdMode = true;
      beep();
      setStatus('\uD83C\uDF99 Listening for command\u2026', 'command');
      clearTimeout(cmdTimer);
      cmdTimer = setTimeout(function() {
        cmdMode = false;
        setStatus('Listening\u2026 say \u201CHey Chef\u201D', 'listening');
      }, 8000);
      return;
    }
    if (cmdMode) {
      cmdMode = false;
      clearTimeout(cmdTimer);
      handleCmd(t);
    }
  };
}

// ─────────────────────────────────────────────────
// WIRE UP BUTTONS via addEventListener
// This was done as there was issues with on click
// Made by Claude
// ─────────────────────────────────────────────────
function wireButtons() {
  var btnStart = document.getElementById('btnStart');
  var btnStop  = document.getElementById('btnStop');
  var prevBtn  = document.getElementById('prevBtn');
  var nextBtn  = document.getElementById('nextBtn');

  if (btnStart) btnStart.addEventListener('click', function() {
    stopped = false;
    setStatus('Listening\u2026 say \u201CHey Chef\u201D', 'listening');
    safeStart();
  });

  if (btnStop) btnStop.addEventListener('click', function() {
    stopped = true;
    cmdMode = false;
    clearTimeout(cmdTimer);
    safeStop();
    speechSynthesis.cancel();
    setStatus('Stopped', '');
  });

  if (prevBtn) prevBtn.addEventListener('click', function() {
    if (current > 0) { goTo(current - 1); speak('Step ' + (current + 1) + '. ' + steps[current]); }
  });

  if (nextBtn) nextBtn.addEventListener('click', function() {
    if (current < steps.length - 1) { goTo(current + 1); speak('Step ' + (current + 1) + '. ' + steps[current]); }
  });
}

// ─────────────────────────────────────────────────
// INIT — script tag is last in the Django block so
// every DOM element above already exists right now.
// Was issues with the JS not loading correctly
// Made by Claude
// ─────────────────────────────────────────────────

if (steps.length === 0) {
  setStatus('No steps found for this recipe.', '');
  document.getElementById('prevBtn').disabled = true;
  document.getElementById('nextBtn').disabled = true;
} else {
  renderSteps();
  goTo(0);
  wireButtons();
  setupRecog();

  if (recog) {
    setStatus('Ready \u2014 click Start to enable voice control', '');
  } else {
    setStatus('Voice unavailable', '');
  }
}