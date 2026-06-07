        // Auth Protection
        const token = localStorage.getItem('token');
        if (!token) window.location.href = 'login.html';

        async function apiFetch(url, options = {}) {
            const headers = {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                ...options.headers
            };
            const response = await fetch(url, { ...options, headers });
            if (response.status === 401) {
                localStorage.removeItem('token');
                window.location.href = 'login.html';
            }
            return response;
        }

        // Initialize User Info
        if (token) {
            apiFetch('http://localhost:8000/me')
                .then(res => res.json())
                .then(user => { if(user.email) document.getElementById('user-email').innerText = user.email; })
                .catch(() => {});
        }

        document.getElementById('logout-btn').onclick = () => {
            localStorage.removeItem('token');
            window.location.href = 'login.html';
        };

        // State Management
        let savedBots = JSON.parse(localStorage.getItem('savedBots') || '[]');
        let currentBot = null;
        let pollInterval;

        // Elements
        const createBtn = document.getElementById('create-btn');
        const urlInput = document.getElementById('url-input');
        const statusSection = document.getElementById('status-section');
        const successArea = document.getElementById('success-area');
        const botList = document.getElementById('bot-list');
        const saveBotBtn = document.getElementById('save-bot-btn');

        // Navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.onclick = () => {
                const target = item.getAttribute('data-target');
                if (!target) return;
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                document.querySelectorAll('.section-content').forEach(s => s.classList.remove('active'));
                document.getElementById(target).classList.add('active');
                
                if (target === 'my-bots-section') renderBotList();
                if (target === 'leads-section') loadAllLeads();
                if (target === 'orders-section') loadOrders();
            };
        });

        // Pipeline Logic
        createBtn.onclick = async () => {
            const url = urlInput.value.trim();
            const fbUrl = document.getElementById('fb-url-input').value.trim();
            if (!url) return alert('Enter URL');
            
            createBtn.disabled = true;
            statusSection.style.display = 'block';
            successArea.style.display = 'none';
            updateProgress('Initiating crawl...', 15);

            try {
                const res = await apiFetch('http://localhost:8000/create-bot', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url, facebook_url: fbUrl || null})
                });
                const data = await res.json();
                currentBot = { id: data.bot_id, url: url, facebook_url: fbUrl, code: data.embed_code };
                startPolling();
            } catch (e) {
                alert('Backend Offline');
                createBtn.disabled = false;
            }
        };

        function startPolling() {
            if (!currentBot || !currentBot.id) return;
            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(async () => {
                if (!currentBot || !currentBot.id) {
                    clearInterval(pollInterval);
                    return;
                }
                const res = await apiFetch(`http://localhost:8000/bot-status/${currentBot.id}`);
                const data = await res.json();
                if (data.status === 'crawling') updateProgress('Crawling content...', 45);
                if (data.status === 'vectorizing') updateProgress('Building vector brain...', 75);
                if (data.status === 'ready') {
                    updateProgress('AI Online!', 100);
                    clearInterval(pollInterval);
                    finishCreation();
                }
            }, 2000);
        }

        function updateProgress(txt, pct) {
            document.getElementById('status-text').innerText = txt;
            document.getElementById('progress-fill').style.width = pct + '%';
            document.getElementById('percent-text').innerText = pct + '%';
        }

        function finishCreation() {
            successArea.style.display = 'block';
            document.getElementById('theme-settings').style.display = 'block';
            document.getElementById('embed-code').innerText = currentBot.code;
            createBtn.disabled = false;
            loadSuggestions(currentBot.id);
            syncThemeUI();
        }

        function syncThemeUI() {
            const primary = document.getElementById('theme-color').value;
            const secondary = document.getElementById('secondary-theme-color').value;
            const name = document.getElementById('bot-display-name').value;
            const welcome = document.getElementById('bot-welcome-msg').value;

            document.getElementById('mini-name').innerText = name;
            document.getElementById('mini-msg').innerText = welcome;
            document.getElementById('mini-header').style.background = primary;
            document.getElementById('mini-send').style.background = primary;
            document.getElementById('mini-msg').style.background = '#1a1f2e'; // Bot bubble
            
            // Sync business name field if it exists
            if (document.getElementById('business-name')) {
                // optional: update mini preview with business name if needed
            }
            
            // User message in preview
            const userMsg = document.querySelector('.msg-user');
            if (userMsg) userMsg.style.background = secondary;
            
            document.getElementById('theme-color-hex').value = primary;
            document.getElementById('secondary-theme-color-hex').value = secondary;
        }

        window.updateLivePreview = () => {
            const primaryInp = document.getElementById('theme-color');
            const primaryHex = document.getElementById('theme-color-hex');
            const secondaryInp = document.getElementById('secondary-theme-color');
            const secondaryHex = document.getElementById('secondary-theme-color-hex');
            
            if (event && event.target === primaryHex) {
                if (/^#[0-9A-F]{6}$/i.test(primaryHex.value)) primaryInp.value = primaryHex.value;
            } else {
                primaryHex.value = primaryInp.value;
            }

            if (event && event.target === secondaryHex) {
                if (/^#[0-9A-F]{6}$/i.test(secondaryHex.value)) secondaryInp.value = secondaryHex.value;
            } else {
                secondaryHex.value = secondaryInp.value;
            }
            
            syncThemeUI();
            
            // Actual Chat Window Preview
            const previewHeader = document.querySelector('.preview-header');
            if (previewHeader) {
                previewHeader.style.background = primaryInp.value;
                document.getElementById('preview-send').style.background = primaryInp.value;
                document.querySelector('.preview-header span').innerText = document.getElementById('bot-display-name').value;
                document.querySelector('.msg-bot').innerText = document.getElementById('bot-welcome-msg').value;
            }
        };

        async function saveTheme() {
            if (!currentBot) return;
            const btn = document.getElementById('save-theme-btn');
            btn.innerText = 'Saving...';
            
            const settings = {
                primary_color: document.getElementById('theme-color').value,
                secondary_color: document.getElementById('secondary-theme-color').value,
                bot_name: document.getElementById('bot-display-name').value,
                business_name: document.getElementById('business-name').value,
                welcome_msg: document.getElementById('bot-welcome-msg').value,
                avatar_url: '',
                lead_capture_enabled: document.getElementById('lead-capture-toggle').checked
            };
            
            try {
                await apiFetch(`http://localhost:8000/bot-settings/${currentBot.id}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(settings)
                });
                btn.innerText = 'Saved!';
                setTimeout(() => btn.innerText = 'Save Changes', 2000);
            } catch (e) {
                alert('Error saving settings');
                btn.innerText = 'Save Changes';
            }
        };

        async function loadSuggestions(bot_id) {
            const area = document.getElementById('suggestions-area');
            area.innerHTML = '<span style="font-size: 10px; color: var(--text-dim);">Loading suggestions...</span>';
            
            try {
                const res = await apiFetch(`http://localhost:8000/suggested-questions/${bot_id}`);
                const data = await res.json();
                renderSuggestions(data.questions);
            } catch (e) {
                area.innerHTML = '';
            }
        }

        function renderSuggestions(questions) {
            const area = document.getElementById('suggestions-area');
            const limited = questions.slice(0, 3);
            area.innerHTML = limited.map(q => `
                <div class="suggestion-pill" style="max-width: 220px; font-size: 11px; padding: 6px 12px; border: 1px solid var(--accent); border-radius: 20px; cursor: pointer; color: var(--accent); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" onclick="useSuggestion('${q}')">${q}</div>
            `).join('');
            
            if (limited.length > 0) {
                const refreshBtn = document.createElement('button');
                refreshBtn.className = 'refresh-btn';
                refreshBtn.style.padding = '4px 8px';
                refreshBtn.style.fontSize = '10px';
                refreshBtn.innerText = 'Refresh';
                refreshBtn.onclick = refreshSuggestions;
                area.appendChild(refreshBtn);
            }
        }

        window.useSuggestion = (q) => {
            const inp = document.getElementById('preview-input');
            inp.value = q;
            document.getElementById('preview-send').click();
        };

        window.refreshSuggestions = async () => {
            if (!currentBot) return;
            const area = document.getElementById('suggestions-area');
            area.innerHTML = '<span style="font-size: 10px; color: var(--text-dim);">Refreshing...</span>';
            const res = await apiFetch(`http://localhost:8000/refresh-suggestions/${currentBot.id}`, {method: 'POST'});
            const data = await res.json();
            renderSuggestions(data.questions);
        };

        // Save Logic
        saveBotBtn.onclick = () => {
            if (!currentBot) return;
            showToast('Bot successfully added to your library!');
            document.querySelector('[data-target="my-bots-section"]').click();
        };

        async function renderBotList() {
            botList.innerHTML = '<p style="color: var(--text-dim);">Loading your bots...</p>';
            try {
                const res = await apiFetch('http://localhost:8000/bots');
                const bots = await res.json();
                
                if (bots.length === 0) {
                    botList.innerHTML = '<p style="color: var(--text-dim);">No bots found. Create your first bot above!</p>';
                    return;
                }
                
                botList.innerHTML = bots.map(bot => `
                    <div class="bot-card">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <h4>${bot.url.split('//')[1]?.split('/')[0] || bot.url}</h4>
                            ${bot.facebook_url ? '<span style="background: #1877F2; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;">FB</span>' : ''}
                        </div>
                        <p>ID: ${bot.bot_id}</p>
                        <p style="font-size: 10px; color: var(--text-dim); margin-bottom: 10px;">Status: ${bot.status}</p>
                        <div style="display: flex; gap: 8px;">
                            <button style="padding: 8px 12px; font-size: 12px;" onclick="loadBotForEdit('${bot.bot_id}')">Edit</button>
                            <button style="padding: 8px 12px; font-size: 12px;" onclick="copySavedCode('${bot.bot_id}')">Code</button>
                            <button class="secondary" style="padding: 8px 12px; font-size: 12px;" onclick="deleteBot('${bot.bot_id}')">Delete</button>
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                botList.innerHTML = '<p style="color: #ff4b2b;">Error loading bots.</p>';
            }
        }

        document.getElementById('save-theme-btn').onclick = saveTheme;

        async function loadBotForEdit(bot_id) {
            const bot = savedBots.find(b => b.id === bot_id);
            if (!bot) return;

            // Switch to dashboard tab
            document.querySelector('[data-target="dashboard-section"]').click();
            
            // UI state
            successArea.style.display = 'block';
            document.getElementById('theme-settings').style.display = 'block';
            
            // Fetch current settings
            try {
                const res = await apiFetch(`http://localhost:8000/bot-settings/${bot_id}`);
                const settings = await res.json();
                
                // Populate UI
                currentBot = { id: bot_id, url: bot.url, code: bot.code };
                document.getElementById('theme-color').value = settings.primary_color;
                document.getElementById('theme-color-hex').value = settings.primary_color;
                document.getElementById('secondary-theme-color').value = settings.secondary_color || '#6366f1';
                document.getElementById('secondary-theme-color-hex').value = settings.secondary_color || '#6366f1';
                document.getElementById('bot-display-name').value = settings.bot_name;
                document.getElementById('bot-welcome-msg').value = settings.welcome_msg;
                document.getElementById('lead-capture-toggle').checked = settings.lead_capture_enabled;
                document.getElementById('embed-code').innerText = currentBot.code;
                
                const bizNameInput = document.getElementById('business-name');
                if (bizNameInput) bizNameInput.value = settings.business_name || '';
                
                updateLivePreview();
                loadSuggestions(bot_id);
            } catch (e) {
                console.error('Error loading bot settings:', e);
            }
        }

        window.loadAllLeads = async () => {
            try {
                const leads = await apiFetch('http://localhost:8000/all-leads');
                const tbody = document.getElementById('leads-table-body');
                tbody.innerHTML = '';
                
                let hotCount = 0;
                let totalScore = 0;
                let posCount = 0;

                leads.forEach(l => {
                    const score = l.lead_score || 0;
                    totalScore += score;
                    if (score >= 7) hotCount++;
                    if (l.sentiment === 'positive') posCount++;

                    const scoreColor = score >= 7 ? '#00ff88' : (score >= 4 ? '#ffb800' : '#ff4b2b');
                    
                    const tr = document.createElement('tr');
                    tr.style.borderBottom = '1px solid #1a1f2e';
                    tr.style.cursor = 'pointer';
                    tr.onclick = () => showLeadModal(l);
                    tr.innerHTML = `
                        <td style="padding: 15px;">
                            <div style="font-weight: bold;">${l.contact_info}</div>
                        </td>
                        <td style="padding: 15px; color: var(--text-dim);">${l.bot_id}</td>
                        <td style="padding: 15px;"><span class="badge" style="background: rgba(0,210,255,0.1); color: var(--accent); padding: 4px 8px; border-radius: 4px; font-size: 10px;">${l.intent || 'inquiry'}</span></td>
                        <td style="padding: 15px;">${l.sentiment || 'neutral'}</td>
                        <td style="padding: 15px;">
                            <div style="display: flex; align-items: center; gap: 5px;">
                                <div style="width: 8px; height: 8px; background: ${scoreColor}; border-radius: 50%;"></div>
                                ${score}
                            </div>
                        </td>
                        <td style="padding: 15px; color: var(--accent); text-decoration: underline; font-size: 11px;">
                            View Summary
                        </td>
                        <td style="padding: 15px; color: var(--text-dim);">${new Date(l.created_at).toLocaleDateString()}</td>
                    `;
                    tbody.appendChild(tr);
                });

                window.currentLeads = leads;
                document.getElementById('stat-total-leads').innerText = leads.length;
                document.getElementById('stat-hot-leads').innerText = hotCount;
                document.getElementById('stat-avg-score').innerText = (totalScore / (leads.length || 1)).toFixed(1);
                document.getElementById('stat-sentiment').innerText = Math.round((posCount / (leads.length || 1)) * 100) + '%';
            } catch (err) {
                console.error("Error loading leads:", err);
            }
        }

        window.loadOrders = async () => {
            try {
                const orders = await apiFetch('http://localhost:8000/all-orders');
                const tbody = document.getElementById('orders-table-body');
                tbody.innerHTML = '';
                
                let pendingCount = 0;
                let totalRev = 0;

                orders.forEach(o => {
                    if (o.status === 'pending') pendingCount++;
                    const price = parseFloat(o.total || 0);
                    totalRev += price;

                    const items = JSON.parse(o.items || '[]');

                    const tr = document.createElement('tr');
                    tr.style.borderBottom = '1px solid #1a1f2e';
                    tr.innerHTML = `
                        <td style="padding: 15px; font-family: monospace;">${o.order_id}</td>
                        <td style="padding: 15px;">
                            <div style="font-weight: bold;">${o.customer_name || 'Anonymous'}</div>
                            <div style="font-size: 11px; color: var(--text-dim);">${o.customer_phone || o.customer_email || ''}</div>
                        </td>
                        <td style="padding: 15px; color: var(--text-dim);">${items.join(', ')}</td>
                        <td style="padding: 15px; font-weight: bold; color: #00ff88;">$${price.toFixed(2)}</td>
                        <td style="padding: 15px;">
                            <select onchange="updateOrderStatus('${o.order_id}', this.value)" style="background: #0b0e14; color: white; border: 1px solid #1a1f2e; padding: 4px; border-radius: 4px; font-size: 11px;">
                                <option value="pending" ${o.status === 'pending' ? 'selected' : ''}>Pending</option>
                                <option value="confirmed" ${o.status === 'confirmed' ? 'selected' : ''}>Confirmed</option>
                                <option value="delivered" ${o.status === 'delivered' ? 'selected' : ''}>Delivered</option>
                                <option value="cancelled" ${o.status === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                            </select>
                        </td>
                        <td style="padding: 15px; color: var(--text-dim);">${new Date(o.created_at).toLocaleDateString()}</td>
                    `;
                    tbody.appendChild(tr);
                });

                window.currentOrders = orders;
                document.getElementById('stat-total-orders').innerText = orders.length;
                document.getElementById('stat-pending-orders').innerText = pendingCount;
                document.getElementById('stat-revenue').innerText = '$' + totalRev.toFixed(2);
            } catch (err) {
                console.error("Error loading orders:", err);
            }
        }

        window.updateOrderStatus = async (order_id, status) => {
            try {
                await apiFetch(`http://localhost:8000/order-status/${order_id}`, {
                    method: 'POST',
                    body: JSON.stringify({ status })
                });
                showToast(`Order ${order_id} updated to ${status}`);
                loadOrders();
            } catch (e) {
                showToast('Error updating order', true);
            }
        }

        function showToast(msg, isError = false) {
            const toast = document.createElement('div');
            toast.style.position = 'fixed';
            toast.style.bottom = '20px';
            toast.style.right = '20px';
            toast.style.background = isError ? '#ff4b2b' : 'var(--accent)';
            toast.style.color = isError ? 'white' : '#0b0e14';
            toast.style.padding = '12px 24px';
            toast.style.borderRadius = '8px';
            toast.style.boxShadow = '0 10px 30px rgba(0,0,0,0.3)';
            toast.style.zIndex = '100000';
            toast.style.fontSize = '14px';
            toast.style.fontWeight = 'bold';
            toast.innerText = msg;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        }

        window.currentLeads = [];
        window.currentOrders = [];

        window.exportLeads = () => {
            if (window.currentLeads.length === 0) return showToast("No leads to export", true);
            const headers = ["Contact", "Bot", "Intent", "Sentiment", "Score", "Summary", "Date"];
            const rows = window.currentLeads.map(l => [
                l.contact_info, l.bot_id, l.intent, l.sentiment, l.lead_score, l.summary.replace(/,/g, ';'), l.created_at
            ]);
            downloadCSV("leads_export", headers, rows);
        };

        window.exportOrders = () => {
            if (window.currentOrders.length === 0) return showToast("No orders to export", true);
            const headers = ["Order ID", "Customer", "Items", "Total", "Status", "Date"];
            const rows = window.currentOrders.map(o => [
                o.order_id, o.customer_name, JSON.parse(o.items).join(';'), o.total, o.status, o.created_at
            ]);
            downloadCSV("orders_export", headers, rows);
        };

        function downloadCSV(filename, headers, rows) {
            let csv = headers.join(",") + "\n";
            rows.forEach(row => {
                csv += row.map(cell => `"${cell}"`).join(",") + "\n";
            });
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.setAttribute('hidden', '');
            a.setAttribute('href', url);
            a.setAttribute('download', `${filename}.csv`);
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }

        window.showLeadModal = (lead) => {
            const overlay = document.getElementById('lead-modal-overlay');
            const body = document.getElementById('modal-body');
            body.innerHTML = `
                <div style="background: #0b0e14; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <div style="color: var(--text-dim); font-size: 11px; text-transform: uppercase;">Conversation Summary</div>
                    <p style="margin-top: 5px;">${lead.summary}</p>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div>
                        <div style="color: var(--text-dim); font-size: 11px;">CONTACT INFO</div>
                        <div style="font-weight: bold;">${lead.contact_info}</div>
                    </div>
                    <div>
                        <div style="color: var(--text-dim); font-size: 11px;">LEAD SCORE</div>
                        <div style="font-weight: bold; color: var(--accent); font-size: 20px;">${lead.lead_score}/10</div>
                    </div>
                </div>
                <div style="margin-top: 20px;">
                    <div style="color: var(--text-dim); font-size: 11px; margin-bottom: 10px;">TRANSCRIPT EXTRACT</div>
                    <div style="background: #0b0e14; padding: 15px; border-radius: 8px; max-height: 200px; overflow-y: auto; font-family: monospace; white-space: pre-wrap; font-size: 12px;">${lead.transcript || 'No transcript available'}</div>
                </div>
            `;
            overlay.style.display = 'flex';
        };

        window.closeModal = () => {
            document.getElementById('lead-modal-overlay').style.display = 'none';
        };

        window.copySavedCode = (id) => {
            const code = `<script src="http://localhost:8000/widget.js" data-bot-id="${id}"></scr` + `ipt>`;
            navigator.clipboard.writeText(code);
            showToast('Embed code copied to clipboard!');
        };
        
        window.deleteBot = async (id) => {
            if (!confirm('Are you sure you want to delete this bot? All data will be lost.')) return;
            try {
                await apiFetch(`http://localhost:8000/bot/${id}`, { method: 'DELETE' });
                showToast('Bot deleted successfully');
                renderBotList();
            } catch (e) {
                showToast('Error deleting bot', true);
            }
        };

        // Chat Preview
        document.getElementById('preview-send').onclick = async () => {
            const inp = document.getElementById('preview-input');
            const q = inp.value.trim();
            if (!q || !currentBot) return;

            // Hide suggestions on first message
            document.getElementById('suggestions-area').style.display = 'none';

            addMsg(q, 'user');
            inp.value = '';

            const res = await fetch('http://localhost:8000/query', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({bot_id: currentBot.id, query: q})
            });
            const data = await res.json();
            addMsg(data.answer, 'bot');
        };

        function addMsg(txt, type) {
            const messages = document.getElementById('preview-messages');
            const div = document.createElement('div');
            div.className = `msg msg-${type}`;
            div.innerText = txt;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }

        function copyCode() {
            navigator.clipboard.writeText(document.getElementById('embed-code').innerText);
            alert('Copied');
        }
