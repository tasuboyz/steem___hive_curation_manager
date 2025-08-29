document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('testForm');
    const submitBtn = document.getElementById('submitBtn');
    const resultsSection = document.getElementById('resultsSection');
    const btnText = document.querySelector('.btn-text');
    const spinner = document.querySelector('.spinner');

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        runTest();
    });

    async function runTest() {
        // Reset UI
        setLoading(true);
        hideResults();
        clearResults();

        // Get form data
        const formData = new FormData(form);
        const sample = formData.get('sample');
        const platform = formData.get('platform');
        const minImportance = parseFloat(formData.get('minImportance'));

        try {
            // Call the backend API
            const response = await fetch('/api/test-curation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    sample: sample,
                    platform: platform,
                    min_importance: minImportance
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            displayResults(data);

        } catch (error) {
            console.error('Error:', error);
            displayError('Errore durante il test: ' + error.message);
        } finally {
            setLoading(false);
        }
    }

    function setLoading(isLoading) {
        submitBtn.disabled = isLoading;
        if (isLoading) {
            btnText.style.display = 'none';
            spinner.style.display = 'inline-block';
        } else {
            btnText.style.display = 'inline';
            spinner.style.display = 'none';
        }
    }

    function hideResults() {
        resultsSection.style.display = 'none';
    }

    function showResults() {
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    function clearResults() {
        document.getElementById('postInfo').textContent = '';
        document.getElementById('totalVoters').textContent = '-';
        document.getElementById('totalValue').textContent = '-';
        document.getElementById('votersTableBody').innerHTML = '';
        document.getElementById('webhookResponse').textContent = '';
        document.getElementById('logsOutput').textContent = '';
    }

    function displayResults(data) {
        showResults();

        // Display post info
        const postInfoElement = document.getElementById('postInfo');
        postInfoElement.textContent = JSON.stringify({
            author: data.author,
            permlink: data.permlink,
            previous_permlink: data.previous_permlink,
            platform: data.platform
        }, null, 2);

        // Display voters stats
        const voters = data.post_voters || [];
        document.getElementById('totalVoters').textContent = voters.length;
        
        const totalValue = voters.reduce((sum, voter) => {
            return sum + (voter.steem_vote_value || 0);
        }, 0);
        document.getElementById('totalValue').textContent = totalValue.toFixed(4);

        // Display voters table
        displayVotersTable(voters);

        // Display webhook response
        const webhookElement = document.getElementById('webhookResponse');
        if (data.webhook_response) {
            webhookElement.textContent = JSON.stringify(data.webhook_response, null, 2);
            webhookElement.className = data.webhook_response.status_code === 200 ? 'success' : 'warning';
        } else {
            webhookElement.textContent = 'Nessuna risposta dal webhook';
            webhookElement.className = 'warning';
        }

        // Display logs
        const logsElement = document.getElementById('logsOutput');
        if (data.logs && data.logs.length > 0) {
            logsElement.textContent = data.logs.join('\n');
        } else {
            logsElement.textContent = 'Nessun log disponibile';
        }
    }

    function displayVotersTable(voters) {
        const tableBody = document.getElementById('votersTableBody');
        tableBody.innerHTML = '';

        if (!voters || voters.length === 0) {
            const row = tableBody.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 5;
            cell.textContent = 'Nessun votante trovato';
            cell.style.textAlign = 'center';
            cell.style.fontStyle = 'italic';
            cell.style.color = '#6c757d';
            return;
        }

        // Sort voters by value (descending)
        const sortedVoters = voters.sort((a, b) => {
            return (b.steem_vote_value || 0) - (a.steem_vote_value || 0);
        });

        sortedVoters.forEach(voter => {
            const row = tableBody.insertRow();
            
            // Voter name
            const voterCell = row.insertCell();
            voterCell.textContent = voter.voter || '-';
            
            // RShares
            const rsharesCell = row.insertCell();
            rsharesCell.textContent = formatNumber(voter.rshares || 0);
            
            // Value
            const valueCell = row.insertCell();
            const value = voter.steem_vote_value || 0;
            valueCell.textContent = value.toFixed(4);
            if (value > 0.01) {
                valueCell.style.color = '#28a745';
                valueCell.style.fontWeight = 'bold';
            }
            
            // Importance
            const importanceCell = row.insertCell();
            const importance = voter.importance || 0;
            importanceCell.textContent = importance.toFixed(3);
            if (importance > 0.5) {
                importanceCell.style.color = '#dc3545';
                importanceCell.style.fontWeight = 'bold';
            }
            
            // Delay
            const delayCell = row.insertCell();
            const delay = voter.vote_delay_minutes;
            delayCell.textContent = delay !== undefined ? delay.toString() : '-';
        });
    }

    function displayError(message) {
        showResults();
        
        const errorElement = document.getElementById('logsOutput');
        errorElement.textContent = message;
        errorElement.className = 'error';
        
        // Clear other sections
        document.getElementById('postInfo').textContent = '';
        document.getElementById('totalVoters').textContent = '-';
        document.getElementById('totalValue').textContent = '-';
        document.getElementById('votersTableBody').innerHTML = '';
        document.getElementById('webhookResponse').textContent = '';
    }

    function formatNumber(num) {
        if (num >= 1000000000) {
            return (num / 1000000000).toFixed(1) + 'B';
        } else if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        } else {
            return num.toString();
        }
    }

    // Add some sample data for demonstration
    function addSampleData() {
        const sampleVoters = [
            {
                voter: "steemcurator01",
                rshares: 1500000000,
                steem_vote_value: 0.5234,
                importance: 0.8,
                vote_delay_minutes: 15
            },
            {
                voter: "cryptopie",
                rshares: 850000000,
                steem_vote_value: 0.2156,
                importance: 0.6,
                vote_delay_minutes: 5
            },
            {
                voter: "hive-engine",
                rshares: 650000000,
                steem_vote_value: 0.1876,
                importance: 0.4,
                vote_delay_minutes: 30
            }
        ];

        // Uncomment below to test with sample data
        // displayResults({
        //     author: "cryptopie",
        //     permlink: "test-permlink",
        //     previous_permlink: "previous-test-permlink",
        //     platform: "steem",
        //     post_voters: sampleVoters,
        //     webhook_response: { status_code: 200, message: "Success" },
        //     logs: ["Test started", "Found 3 voters", "Webhook sent successfully"]
        // });
    }
});
