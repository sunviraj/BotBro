(function() {
    // Get bot_id from script tag
    const scriptTag = document.currentScript;
    const botId = scriptTag ? scriptTag.getAttribute('data-bot-id') : 'default';
    const baseUrl = 'http://localhost:8000';
    const sessionId = 'sess-' + Math.random().toString(36).substr(2, 9);

    // Create CSS with variables
    const style = document.createElement('style');
    style.innerHTML = `
        :root {
            --sitegpt-primary: #00d2ff;
            --sitegpt-secondary: #6366f1;
        }
        #sitegpt-widget-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 10000;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        #sitegpt-button {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: var(--sitegpt-primary);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        #sitegpt-button:hover { transform: scale(1.1); }
        #sitegpt-button svg { width: 30px; height: 30px; fill: white; }
        
        #sitegpt-chat-window {
            position: absolute;
            bottom: 80px;
            right: 0;
            width: 350px;
            height: 500px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
            display: none;
            flex-direction: column;
            overflow: hidden;
            border: 1px solid #eee;
        }
        #sitegpt-chat-header {
            padding: 20px;
            background: var(--sitegpt-primary);
            color: white;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }
        #sitegpt-chat-header h3 { margin: 0; font-size: 16px; color: white; }
        #sitegpt-chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 15px;
            background: #fff;
        }
        .sitegpt-message {
            padding: 12px 16px;
            border-radius: 15px;
            max-width: 80%;
            font-size: 14px;
            line-height: 1.4;
            position: relative;
        }
        .sitegpt-user {
            background: var(--sitegpt-secondary);
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }
        .sitegpt-bot {
            background: #f1f3f5;
            color: #333;
            align-self: flex-start;
            border-bottom-left-radius: 4px;
        }
        .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 4px 0;
            align-items: center;
        }
        .typing-indicator span {
            width: 6px;
            height: 6px;
            background: #90949c;
            border-radius: 50%;
            animation: typing 1.4s infinite ease-in-out both;
        }
        .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
        .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
        @keyframes typing {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        #sitegpt-chat-input {
            padding: 15px;
            border-top: 1px solid #eee;
            display: flex;
            gap: 10px;
            background: white;
        }
        #sitegpt-chat-input input {
            flex: 1;
            border: 1px solid #ddd;
            padding: 10px 15px;
            border-radius: 25px;
            outline: none;
            font-size: 14px;
        }
        #sitegpt-chat-input button {
            background: var(--sitegpt-primary);
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
        }
        .typing-indicator {
            align-self: flex-start;
            padding: 12px 16px;
            background: #f1f3f5;
            border-radius: 15px;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .typing-indicator span {
            width: 6px;
            height: 6px;
            background: var(--sitegpt-primary);
            border-radius: 50%;
            animation: typingPulse 1.2s infinite ease-in-out;
            opacity: 0.4;
        }
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typingPulse {
            0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
            40% { transform: scale(1); opacity: 1; }
        }
        .blinking-cursor::after {
            content: '|';
            display: inline-block;
            margin-left: 2px;
            animation: cursorBlink 1s infinite;
            color: var(--sitegpt-primary);
        }
        @keyframes cursorBlink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
        }
        #sitegpt-suggestions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            padding: 10px 20px;
            background: white;
        }
        .sitegpt-pill {
            padding: 6px 12px;
            border: 1px solid var(--sitegpt-primary);
            border-radius: 20px;
            font-size: 12px;
            cursor: pointer;
            color: var(--sitegpt-primary);
            transition: 0.2s;
            max-width: 220px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .sitegpt-pill:hover { background: var(--sitegpt-primary); color: white; }
        
        #sitegpt-sound-toggle {
            cursor: pointer;
            opacity: 0.7;
            font-size: 14px;
        }
        #sitegpt-sound-toggle:hover { opacity: 1; }
        
        /* Lead Capture Form */
        #sitegpt-lead-capture {
            display: flex;
            flex-direction: column;
            padding: 30px 20px;
            text-align: center;
            background: white;
            flex: 1;
            justify-content: center;
            gap: 15px;
        }
        #sitegpt-lead-capture h4 {
            margin: 0;
            color: #333;
            font-size: 18px;
        }
        #sitegpt-lead-capture p {
            margin: 0;
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }
        #sitegpt-lead-capture input {
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            outline: none;
        }
        #sitegpt-lead-capture input:focus {
            border-color: var(--sitegpt-primary);
        }
        #sitegpt-lead-capture button {
            padding: 12px;
            background: var(--sitegpt-primary);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 5px;
        }
        
        /* Chat UI Container (Hidden initially) */
        #sitegpt-chat-ui {
            display: none;
            flex-direction: column;
            flex: 1;
            overflow: hidden;
        }

        /* Attachment Button */
        #sitegpt-attach-btn {
            background: transparent;
            border: none;
            cursor: pointer;
            padding: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0.6;
            transition: 0.2s;
        }
        #sitegpt-attach-btn:hover {
            opacity: 1;
        }
        #sitegpt-attach-btn svg {
            width: 20px;
            height: 20px;
            fill: #666;
        }
        #sitegpt-file-input {
            display: none;
        }
        #sitegpt-image-preview-container {
            display: none;
            padding: 10px 20px;
            background: #f9f9f9;
            border-top: 1px solid #eee;
            position: relative;
        }
        #sitegpt-image-preview {
            max-height: 60px;
            border-radius: 8px;
        }
        #sitegpt-remove-image {
            position: absolute;
            top: 5px;
            right: 15px;
            background: #ff4444;
            color: white;
            border: none;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            cursor: pointer;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        /* Markdown Image Styling */
        .sitegpt-message img {
            max-width: 100%;
            border-radius: 8px;
            margin: 8px 0;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .sitegpt-message img:hover {
            transform: scale(1.02);
        }
        .sitegpt-message a {
            color: var(--sitegpt-primary);
            font-weight: bold;
            text-decoration: none;
        }
        .sitegpt-message a:hover {
            text-decoration: underline;
        }
    `;
    document.head.appendChild(style);

    // Create HTML
    const container = document.createElement('div');
    container.id = 'sitegpt-widget-container';
    container.innerHTML = `
        <div id="sitegpt-chat-window">
            <div id="sitegpt-chat-header">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 10px; height: 10px; background: #4CAF50; border-radius: 50%;"></div>
                    <h3 id="sitegpt-header-name">Assistant</h3>
                </div>
                <div id="sitegpt-sound-toggle" title="Toggle sound">🔈</div>
            </div>
            
            <div id="sitegpt-lead-capture">
                <h4>Welcome! 👋</h4>
                <p>Please enter your details to start chatting.</p>
                <input type="text" id="sitegpt-lead-name" placeholder="Your Name" required>
                <input type="tel" id="sitegpt-lead-phone" placeholder="Phone Number" required>
                <button id="sitegpt-lead-submit">Start Chat</button>
            </div>

            <div id="sitegpt-chat-ui">
                <div id="sitegpt-chat-messages">
                    <div id="sitegpt-welcome" class="sitegpt-message sitegpt-bot">Hi! How can I help you today?</div>
                </div>
                <div id="sitegpt-suggestions"></div>
                <div id="sitegpt-image-preview-container">
                    <img id="sitegpt-image-preview" src="" alt="Preview">
                    <button id="sitegpt-remove-image">×</button>
                </div>
                <div id="sitegpt-chat-input">
                    <button id="sitegpt-attach-btn" title="Attach Image">
                        <svg viewBox="0 0 24 24"><path d="M16.5,6v11.5c0,2.21-1.79,4-4,4s-4-1.79-4-4V5c0-1.38,1.12-2.5,2.5-2.5s2.5,1.12,2.5,2.5v10.5c0,0.55-0.45,1-1,1s-1-0.45-1-1V6H10v9.5c0,1.38,1.12,2.5,2.5,2.5s2.5-1.12,2.5-2.5V5c0-2.21-1.79-4-4-4S7,2.79,7,5v12.5c0,3.04,2.46,5.5,5.5,5.5s5.5-2.46,5.5-5.5V6H16.5z"/></svg>
                    </button>
                    <input type="file" id="sitegpt-file-input" accept="image/*">
                    <input type="text" placeholder="Type your message..." id="sitegpt-query-input">
                    <button id="sitegpt-send-btn">Send</button>
                </div>
            </div>
        </div>
        <div id="sitegpt-button">
            <svg viewBox="0 0 24 24"><path d="M20,2H4C2.9,2,2,2.9,2,4v18l4-4h14c1.1,0,2-0.9,2-2V4C22,2.9,21.1,2,20,2z"/></svg>
        </div>
    `;
    document.body.appendChild(container);

    // Elements
    const btn = document.getElementById('sitegpt-button');
    const chatWin = document.getElementById('sitegpt-chat-window');
    const chatUi = document.getElementById('sitegpt-chat-ui');
    const leadCapture = document.getElementById('sitegpt-lead-capture');
    const input = document.getElementById('sitegpt-query-input');
    const sendBtn = document.getElementById('sitegpt-send-btn');
    const messages = document.getElementById('sitegpt-chat-messages');
    const suggestions = document.getElementById('sitegpt-suggestions');
    const soundBtn = document.getElementById('sitegpt-sound-toggle');

    const leadName = document.getElementById('sitegpt-lead-name');
    const leadPhone = document.getElementById('sitegpt-lead-phone');
    const leadSubmit = document.getElementById('sitegpt-lead-submit');

    const attachBtn = document.getElementById('sitegpt-attach-btn');
    const fileInput = document.getElementById('sitegpt-file-input');
    const previewContainer = document.getElementById('sitegpt-image-preview-container');
    const previewImage = document.getElementById('sitegpt-image-preview');
    const removeImage = document.getElementById('sitegpt-remove-image');

    // Local state
    let msgCount = 0;
    let leadCaptured = false;
    let botSettings = null;
    let soundEnabled = false;
    let audioCtx = null;
    let selectedImageBase64 = null;

    // Fetch Settings
    fetch(`${baseUrl}/bot-settings/${botId}`)
        .then(res => res.json())
        .then(settings => {
            botSettings = settings;
            document.documentElement.style.setProperty('--sitegpt-primary', settings.primary_color);
            document.documentElement.style.setProperty('--sitegpt-secondary', settings.secondary_color || '#6366f1');
            document.getElementById('sitegpt-header-name').innerText = settings.bot_name;
            document.getElementById('sitegpt-welcome').innerText = settings.welcome_msg;
            loadSuggestions();
        })
        .catch(err => console.log("SiteGPT: Using default theme"));

    const loadSuggestions = () => {
        fetch(`${baseUrl}/suggested-questions/${botId}`)
            .then(res => res.json())
            .then(data => {
                suggestions.innerHTML = '';
                data.questions.slice(0, 3).forEach(q => {
                    const pill = document.createElement('div');
                    pill.className = 'sitegpt-pill';
                    pill.innerText = q;
                    pill.title = q;
                    pill.onclick = () => {
                        input.value = q;
                        sendMessage();
                    };
                    suggestions.appendChild(pill);
                });
            });
    };

    // Sound Logic
    soundBtn.onclick = () => {
        soundEnabled = !soundEnabled;
        soundBtn.innerText = soundEnabled ? '🔊' : '🔈';
        if (soundEnabled && !audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
    };

    const playTick = () => {
        if (!soundEnabled || !audioCtx) return;
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(800, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.05, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.03);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.03);
    };

    // Lead Capture Logic
    leadSubmit.onclick = () => {
        const name = leadName.value.trim();
        const phone = leadPhone.value.trim();
        if (!name || !phone) {
            alert('Please enter your name and phone number to start chatting.');
            return;
        }
        
        // Submit lead to backend
        fetch(`${baseUrl}/submit-lead/${botId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, phone: phone, session_id: sessionId })
        }).catch(err => console.log('Lead capture error', err));

        leadCaptured = true;
        leadCapture.style.display = 'none';
        chatUi.style.display = 'flex';
        
        // Scroll to bottom
        messages.scrollTop = messages.scrollHeight;
    };

    // Attachment Logic
    attachBtn.onclick = () => fileInput.click();
    fileInput.onchange = (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (evt) => {
                selectedImageBase64 = evt.target.result;
                previewImage.src = selectedImageBase64;
                previewContainer.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    };
    removeImage.onclick = () => {
        selectedImageBase64 = null;
        previewContainer.style.display = 'none';
        fileInput.value = '';
    };

    const parseMarkdown = (text) => {
        // Parse markdown images [![alt](img_url)](link_url)
        let html = text.replace(/\[!\[(.*?)\]\((.*?)\)\]\((.*?)\)/g, '<a href="$3" target="_blank"><img src="$2" alt="$1"></a>');
        // Parse standard markdown images ![alt](url)
        html = html.replace(/!\[(.*?)\]\((.*?)\)/g, '<img src="$2" alt="$1">');
        // Parse markdown links [text](url)
        html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
        // Parse bold text **text**
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Parse bold text *text*
        html = html.replace(/\*(.*?)\*/g, '<strong>$1</strong>');
        return html;
    };

    const streamMessage = async (text) => {
        const msg = document.createElement('div');
        msg.className = 'sitegpt-message sitegpt-bot blinking-cursor';
        messages.appendChild(msg);
        
        // If there's markdown, skip streaming for images/links to avoid breaking HTML tags
        if (text.includes('![') || text.includes('](')) {
            msg.innerHTML = parseMarkdown(text);
            playTick();
            messages.scrollTop = messages.scrollHeight;
        } else {
            const words = text.split(' ');
            for (let i = 0; i < words.length; i++) {
                msg.innerText += (i === 0 ? '' : ' ') + words[i];
                playTick();
                messages.scrollTop = messages.scrollHeight;
                await new Promise(r => setTimeout(r, 40 + Math.random() * 40));
            }
        }
        msg.classList.remove('blinking-cursor');
    };

    const addMessage = (text, type, imageBase64 = null) => {
        const msg = document.createElement('div');
        msg.className = `sitegpt-message sitegpt-${type}`;
        
        let content = parseMarkdown(text);
        if (imageBase64) {
            content += `<br><img src="${imageBase64}" style="max-height: 100px; margin-top: 10px;">`;
        }
        msg.innerHTML = content;
        
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
    };

    const showTypingIndicator = () => {
        const msg = document.createElement('div');
        msg.className = 'sitegpt-message sitegpt-bot typing-bubble';
        msg.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
        return msg;
    };

    const sendMessage = async () => {
        const query = input.value.trim();
        if (!query) return;

        // Remove suggestions after first message
        if (msgCount === 0) suggestions.style.display = 'none';

        addMessage(query, 'user', selectedImageBase64);
        
        const payload = { bot_id: botId, query: query, session_id: sessionId };
        if (selectedImageBase64) {
            payload.image_base64 = selectedImageBase64;
            // Clear selection after sending
            removeImage.onclick();
        }

        input.value = '';
        msgCount++;

        const typingMsg = showTypingIndicator(); // Show typing indicator

        try {
            const response = await fetch(`${baseUrl}/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            
            // Wait a bit for "thinking" feel
            await new Promise(r => setTimeout(r, 600));
            typingMsg.remove(); // Remove indicator
            
            await streamMessage(data.answer);

        } catch (e) {
            typingMsg.remove();
            addMessage("Sorry, I'm having trouble connecting to my brain right now.", "bot");
        }
    };

    // Session end tracking
    const endSession = () => {
        if (msgCount === 0) return;
        fetch(`${baseUrl}/bot/${botId}/end-session`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId }),
            keepalive: true
        });
    };

    window.addEventListener('beforeunload', endSession);
    
    sendBtn.onclick = sendMessage;
    input.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
})();
