document.addEventListener("DOMContentLoaded", () => {
    // Resolve the API URL
    let API_BASE_URL = localStorage.getItem("custom_api_url");
    if (!API_BASE_URL) {
        if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
            // If we are on localhost but not on port 8000 (e.g., Live Server), target the backend at port 8000
            API_BASE_URL = window.location.port === "8000" ? "" : "http://localhost:8000";
        } else if (window.location.hostname.endsWith(".railway.app")) {
            API_BASE_URL = "";
        } else {
            API_BASE_URL = "https://restaurant-recommender-production.up.railway.app";
        }
    }

    // State management
    let selectedBudget = "medium";
    let selectedRating = 4.0;
    
    // Core search result states for live sorting & filtering
    let lastResultsData = null; 
    let activeSort = "rank";
    let activeFilterQuery = "";

    // Persistent storage states
    let favorites = JSON.parse(localStorage.getItem("favorite_restaurants") || "[]");
    let history = JSON.parse(localStorage.getItem("recommendation_history") || "[]");

    // DOM Elements - Form inputs
    const locationSelect = document.getElementById("location-select");
    const cuisineSelect = document.getElementById("cuisine-select");
    const additionalPrefs = document.getElementById("additional-preferences");
    const generateBtn = document.getElementById("generate-btn");
    
    // DOM Elements - Status and Views
    const emptyState = document.getElementById("empty-state");
    const loadingState = document.getElementById("loading-state");
    const resultsContainer = document.getElementById("results-container");
    const resultsSummaryText = document.getElementById("results-summary-text");
    const resultsList = document.getElementById("results-list");
    const errorBanner = document.getElementById("error-banner");
    const errorMessage = document.getElementById("error-message");
    const relaxationBanner = document.getElementById("relaxation-banner");
    const relaxationMessage = document.getElementById("relaxation-message");

    const connectionDot = document.getElementById("connection-dot");
    const connectionText = document.getElementById("connection-text");
    const footerHealthDot = document.getElementById("footer-health-dot");
    const footerHealthText = document.getElementById("footer-health-text");

    // DOM Elements - Navigation buttons & Views
    const navDiscover = document.getElementById("nav-discover");
    const navCollections = document.getElementById("nav-collections");
    const navHistory = document.getElementById("nav-history");
    const navFavorites = document.getElementById("nav-favorites");

    const viewDiscover = document.getElementById("view-discover");
    const viewCollections = document.getElementById("view-collections");
    const viewHistory = document.getElementById("view-history");
    const viewFavorites = document.getElementById("view-favorites");

    // DOM Elements - Sorting & Filtering
    const filterSearchInput = document.getElementById("filter-search-input");
    const sortSelect = document.getElementById("sort-select");

    // Curated Collections Database
    const collectionsData = [
        {
            id: "cp-elite",
            title: "Connaught Place Fine Dining",
            description: "High-end North Indian and Mughlai culinary masterworks in the heart of Delhi.",
            location: "Connaught Place",
            cuisine: "North Indian",
            budget: "high",
            rating: 4.0,
            icon: "wine_bar"
        },
        {
            id: "hkv-continental",
            title: "Hauz Khas Village Cafes",
            description: "A selection of trendy Italian and Continental cafes overlooking the lake.",
            location: "Hauz Khas Village",
            cuisine: "Continental",
            budget: "medium",
            rating: 4.0,
            icon: "local_cafe"
        },
        {
            id: "cp-budget",
            title: "CP Street Food & Quick Bites",
            description: "Delhi's legendary local street food and fast-casual favorites on a budget.",
            location: "Connaught Place",
            cuisine: "Street Food",
            budget: "low",
            rating: 3.5,
            icon: "fastfood"
        },
        {
            id: "nsp-desserts",
            title: "NSP Desserts & Shakes",
            description: "Sweet spot recommendations in Netaji Subhash Place for quick desserts.",
            location: "Netaji Subhash Place",
            cuisine: "Desserts",
            budget: "low",
            rating: 4.0,
            icon: "icecream"
        },
        {
            id: "rajouri-chinese",
            title: "Rajouri Garden Chinese Feast",
            description: "Top-tier Asian cuisine and authentic Chinese restaurants in West Delhi.",
            location: "Rajouri Garden",
            cuisine: "Chinese",
            budget: "medium",
            rating: 4.0,
            icon: "soup_kitchen"
        },
        {
            id: "nfc-mughlai",
            title: "New Friends Colony Mughlai",
            description: "Rich, aromatic kebabs and historic Mughlai curries in South Delhi.",
            location: "New Friends Colony",
            cuisine: "Mughlai",
            budget: "medium",
            rating: 4.0,
            icon: "dinner_dining"
        }
    ];

    // Initialize Page
    checkSystemHealth();
    loadMetadata();
    setupBudgetSelector();
    setupStarRating();
    setupNavigation();
    setupSortingAndFiltering();

    // Configuration Handler for API Base URL
    const triggerUrlPrompt = () => {
        const currentUrl = localStorage.getItem("custom_api_url") || "";
        const newUrl = prompt(
            "Configure Backend API URL\n\nEnter your deployed Railway backend URL (e.g., https://your-app.up.railway.app):\nLeave blank to reset to default.",
            currentUrl
        );
        
        if (newUrl !== null) {
            const trimmedUrl = newUrl.trim();
            if (trimmedUrl) {
                const cleanUrl = trimmedUrl.replace(/\/+$/, "");
                localStorage.setItem("custom_api_url", cleanUrl);
            } else {
                localStorage.removeItem("custom_api_url");
            }
            window.location.reload();
        }
    };

    // Event Listeners
    generateBtn.addEventListener("click", handleGenerate);
    
    const settingsBtn = document.getElementById("settings-btn");
    if (settingsBtn) {
        settingsBtn.addEventListener("click", triggerUrlPrompt);
    }
    if (connectionDot) {
        connectionDot.style.cursor = "pointer";
        connectionDot.title = "Click to set Backend API URL";
        connectionDot.addEventListener("click", triggerUrlPrompt);
    }
    if (connectionText) {
        connectionText.style.cursor = "pointer";
        connectionText.title = "Click to set Backend API URL";
        connectionText.addEventListener("click", triggerUrlPrompt);
    }

    // 1. Verify health of the API
    async function checkSystemHealth() {
        try {
            const res = await fetch(`${API_BASE_URL}/health`);
            const data = await res.json();
            if (res.ok && data.status === "healthy") {
                updateHealthStatus(true, `System Connected (${data.dataset.restaurant_count} restaurants)`);
            } else {
                updateHealthStatus(false, "Initializing Database...");
            }
        } catch (err) {
            console.error("Health check failed:", err);
            updateHealthStatus(false, "Offline / Connection Error");
        }
    }

    function updateHealthStatus(isHealthy, text) {
        const activeColor = "bg-primary";
        const inactiveColor = "bg-error";
        
        if (isHealthy) {
            connectionDot.className = `w-2 h-2 rounded-full ${activeColor} health-dot`;
            connectionText.textContent = text;
            connectionText.className = "text-label-sm font-label-sm text-primary tracking-wider uppercase";
            
            footerHealthDot.className = `w-1.5 h-1.5 ${activeColor} rounded-full`;
            footerHealthText.textContent = "healthy";
            footerHealthText.className = "font-medium text-primary";
        } else {
            connectionDot.className = `w-2 h-2 rounded-full ${inactiveColor} health-dot`;
            connectionText.textContent = text;
            connectionText.className = "text-label-sm font-label-sm text-error tracking-wider uppercase";
            
            footerHealthDot.className = `w-1.5 h-1.5 ${inactiveColor} rounded-full`;
            footerHealthText.textContent = "initializing";
            footerHealthText.className = "font-medium text-error";
        }
    }

    // 2. Fetch locations to populate filter options
    async function loadMetadata() {
        try {
            // Load Locations
            const locRes = await fetch(`${API_BASE_URL}/api/v1/locations`);
            if (locRes.ok) {
                const locations = await locRes.json();
                locationSelect.innerHTML = "";
                
                // Add placeholder
                const placeholder = document.createElement("option");
                placeholder.value = "";
                placeholder.disabled = true;
                placeholder.selected = true;
                placeholder.textContent = "Select city...";
                locationSelect.appendChild(placeholder);

                locations.forEach(loc => {
                    const opt = document.createElement("option");
                    opt.className = "bg-surface-container capitalize";
                    opt.value = loc;
                    opt.textContent = capitalizeString(loc);
                    locationSelect.appendChild(opt);
                });
            }
        } catch (err) {
            console.error("Failed to load metadata dropdowns:", err);
        }
    }

    // Helper: Capitalize words
    function capitalizeString(str) {
        return str.split(" ").map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
    }

    // 3. Handle budget button interactions
    function setupBudgetSelector() {
        const buttons = document.querySelectorAll(".budget-btn");
        buttons.forEach(btn => {
            btn.addEventListener("click", () => {
                buttons.forEach(b => {
                    b.className = "budget-btn py-3 px-4 rounded-xl border border-white/10 bg-white/5 text-on-surface hover:border-primary/50 transition-all font-label-md shadow-none";
                });
                
                selectedBudget = btn.getAttribute("data-budget");
                btn.className = "budget-btn py-3 px-4 rounded-xl border-2 border-primary bg-primary/10 text-primary transition-all font-label-md shadow-[0_0_15px_rgba(226,55,68,0.2)]";
            });
        });
    }

    // 4. Handle star rating clicks
    function setupStarRating() {
        const starButtons = document.querySelectorAll(".star-btn");
        const ratingValText = document.getElementById("rating-value");

        starButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                selectedRating = parseFloat(btn.getAttribute("data-rating"));
                ratingValText.textContent = `${selectedRating.toFixed(1)}+`;

                // Re-render stars
                starButtons.forEach(star => {
                    const ratingVal = parseFloat(star.getAttribute("data-rating"));
                    const icon = star.querySelector(".material-symbols-outlined");
                    if (ratingVal <= selectedRating) {
                        icon.className = "material-symbols-outlined text-tertiary";
                        icon.style.fontVariationSettings = "'FILL' 1";
                    } else {
                        icon.className = "material-symbols-outlined text-on-surface-variant";
                        icon.style.fontVariationSettings = "'FILL' 0";
                    }
                });
            });
        });
    }

    // 5. Navigation Tab Handler
    function setupNavigation() {
        const tabs = [
            { btn: navDiscover, view: viewDiscover, name: "discover" },
            { btn: navCollections, view: viewCollections, name: "collections" },
            { btn: navHistory, view: viewHistory, name: "history" },
            { btn: navFavorites, view: viewFavorites, name: "favorites" }
        ];

        tabs.forEach(tab => {
            if (tab.btn) {
                tab.btn.addEventListener("click", () => {
                    // Update active styling
                    tabs.forEach(t => {
                        t.btn.className = "w-full flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-on-surface hover:bg-white/5 rounded-lg transition-all";
                        t.view.classList.add("hidden");
                    });

                    tab.btn.className = "w-full flex items-center gap-3 px-4 py-3 bg-primary/10 text-primary border-r-4 border-primary rounded-r-lg group transition-transform hover:translate-x-1";
                    tab.view.classList.remove("hidden");

                    // Trigger specific view loaders
                    if (tab.name === "collections") {
                        renderCollections();
                    } else if (tab.name === "history") {
                        renderHistory();
                    } else if (tab.name === "favorites") {
                        renderFavorites();
                    }
                });
            }
        });
    }

    // 6. Curated Collections Renderer
    function renderCollections() {
        const grid = document.getElementById("collections-grid");
        if (!grid) return;
        grid.innerHTML = "";

        collectionsData.forEach(col => {
            const card = document.createElement("div");
            card.className = "glass-card p-6 rounded-2xl flex flex-col gap-4 cursor-pointer";
            card.innerHTML = `
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
                        <span class="material-symbols-outlined text-2xl">${col.icon}</span>
                    </div>
                    <div class="flex-1">
                        <h3 class="font-display-lg text-headline-sm font-bold text-on-surface">${col.title}</h3>
                        <span class="text-xs text-primary font-medium tracking-wider uppercase">${col.location}</span>
                    </div>
                </div>
                <p class="text-body-md text-on-surface-variant font-light flex-1 leading-relaxed">${col.description}</p>
                <div class="flex items-center justify-between border-t border-white/5 pt-4 mt-2">
                    <span class="text-xs px-2.5 py-0.5 bg-white/5 border border-white/10 rounded-lg text-on-surface-variant capitalize">${col.cuisine} • ${col.budget}</span>
                    <span class="text-xs text-tertiary flex items-center gap-1">
                        <span class="material-symbols-outlined text-sm" style="font-variation-settings: 'FILL' 1;">star</span>
                        ${col.rating}+
                    </span>
                </div>
            `;

            // On click, execute collection query
            card.addEventListener("click", () => {
                // Populate discover inputs
                locationSelect.value = col.location.toLowerCase();
                cuisineSelect.value = col.cuisine;
                
                // Select budget
                const budgetBtn = document.querySelector(`.budget-btn[data-budget="${col.budget}"]`);
                if (budgetBtn) budgetBtn.click();

                // Select rating
                const starBtn = document.querySelector(`.star-btn[data-rating="${Math.floor(col.rating)}"]`);
                if (starBtn) starBtn.click();

                // Clear requirements
                additionalPrefs.value = "";

                // Route to Discover and submit
                navDiscover.click();
                handleGenerate();
            });

            grid.appendChild(card);
        });
    }

    // 7. Search History Logger & Renderer
    function saveToHistory(payload, results) {
        // Prevent duplicate logs
        const duplicateIndex = history.findIndex(h => 
            h.payload.location === payload.location &&
            h.payload.cuisine === payload.cuisine &&
            h.payload.budget === payload.budget &&
            h.payload.min_rating === payload.min_rating &&
            h.payload.additional_preferences === payload.additional_preferences
        );

        if (duplicateIndex !== -1) {
            history.splice(duplicateIndex, 1);
        }

        // Add to front of history
        history.unshift({
            timestamp: new Date().toISOString(),
            payload: payload,
            results: results
        });

        // Limit history to 5 items
        if (history.length > 5) history.pop();

        localStorage.setItem("recommendation_history", JSON.stringify(history));
    }

    function renderHistory() {
        const container = document.getElementById("history-list");
        if (!container) return;
        container.innerHTML = "";

        if (history.length === 0) {
            container.innerHTML = `
                <div class="glass-card p-12 rounded-2xl text-center text-on-surface-variant font-body-md">
                    No recent search history found. Try configuring choices on the Discover page first!
                </div>
            `;
            return;
        }

        history.forEach((hist, index) => {
            const item = document.createElement("div");
            item.className = "glass-card p-6 rounded-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4";
            
            const date = new Date(hist.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' - ' + new Date(hist.timestamp).toLocaleDateString();
            const prefsText = `Location: <strong class="capitalize text-on-surface">${hist.payload.location}</strong> | Cuisine: <strong class="text-on-surface">${hist.payload.cuisine}</strong> | Budget: <strong class="capitalize text-on-surface">${hist.payload.budget}</strong> | Rating: <strong class="text-on-surface">${hist.payload.min_rating}+</strong>`;

            item.innerHTML = `
                <div>
                    <div class="flex items-center gap-2 mb-1">
                        <span class="text-xs text-primary font-medium uppercase tracking-wide">Query #${index + 1}</span>
                        <span class="text-xs text-on-surface-variant/40">•</span>
                        <span class="text-xs text-on-surface-variant">${date}</span>
                    </div>
                    <p class="text-body-md text-on-surface-variant font-light mt-1">${prefsText}</p>
                    ${hist.payload.additional_preferences ? `<p class="text-xs text-primary/70 italic mt-1.5">"${hist.payload.additional_preferences}"</p>` : ""}
                </div>
                <div class="flex gap-3 mt-2 md:mt-0">
                    <button class="px-4 py-2 bg-primary text-on-primary rounded-xl font-label-md hover:opacity-90 active:scale-95 transition-all text-sm reload-btn">
                        View Results
                    </button>
                    <button class="p-2 border border-white/10 hover:border-error/30 hover:bg-error/5 text-on-surface-variant hover:text-error rounded-xl transition-all delete-history-btn">
                        <span class="material-symbols-outlined text-lg">delete</span>
                    </button>
                </div>
            `;

            // Action: Reload cached history results
            item.querySelector(".reload-btn").addEventListener("click", () => {
                // Populate forms
                locationSelect.value = hist.payload.location;
                cuisineSelect.value = hist.payload.cuisine;
                additionalPrefs.value = hist.payload.additional_preferences || "";

                const budgetBtn = document.querySelector(`.budget-btn[data-budget="${hist.payload.budget}"]`);
                if (budgetBtn) budgetBtn.click();

                const starBtn = document.querySelector(`.star-btn[data-rating="${Math.floor(hist.payload.min_rating)}"]`);
                if (starBtn) starBtn.click();

                // Switch to Discover view and immediately render cached data
                navDiscover.click();
                renderResults(hist.results);
            });

            // Action: Delete history entry
            item.querySelector(".delete-history-btn").addEventListener("click", () => {
                history.splice(index, 1);
                localStorage.setItem("recommendation_history", JSON.stringify(history));
                renderHistory();
            });

            container.appendChild(item);
        });
    }

    // 8. Favorites Persistent Storage & Renderer
    function isFavorite(name) {
        return favorites.some(fav => fav.name.toLowerCase() === name.toLowerCase());
    }

    function toggleFavorite(restaurant, eventBtn) {
        const index = favorites.findIndex(fav => fav.name.toLowerCase() === restaurant.name.toLowerCase());
        
        if (index === -1) {
            // Save to favorites
            favorites.push(restaurant);
            eventBtn.querySelector(".material-symbols-outlined").style.fontVariationSettings = "'FILL' 1";
            eventBtn.className = "p-2 bg-primary/20 border border-primary/30 text-primary rounded-xl transition-all fav-btn heart-pop";
        } else {
            // Remove from favorites
            favorites.splice(index, 1);
            eventBtn.querySelector(".material-symbols-outlined").style.fontVariationSettings = "'FILL' 0";
            eventBtn.className = "p-2 bg-white/5 border border-white/10 text-on-surface-variant hover:text-primary rounded-xl transition-all fav-btn";
        }
        
        localStorage.setItem("favorite_restaurants", JSON.stringify(favorites));

        // Clear pop animation after play
        setTimeout(() => {
            eventBtn.classList.remove("heart-pop");
        }, 300);
    }

    // Render Favorites view list
    function renderFavorites() {
        const grid = document.getElementById("favorites-grid");
        if (!grid) return;
        grid.innerHTML = "";

        if (favorites.length === 0) {
            grid.className = "block";
            grid.innerHTML = `
                <div class="glass-card p-12 rounded-2xl text-center text-on-surface-variant font-body-md">
                    No bookmarked restaurants yet. Tap the heart button on recommendation cards in the Discover tab to build your favorites list!
                </div>
            `;
            return;
        }

        grid.className = "grid grid-cols-1 md:grid-cols-2 gap-6";

        favorites.forEach(rec => {
            const card = document.createElement("div");
            card.className = "glass-card overflow-hidden rounded-2xl p-6 flex flex-col gap-4 relative transition-all";

            const cuisineTags = rec.cuisine.split(",").map(c => c.trim());
            const cuisineHTML = cuisineTags.map(c => `
                <span class="text-xs px-2.5 py-0.5 bg-white/5 rounded-lg border border-white/10 text-on-surface-variant capitalize">
                    ${c}
                </span>
            `).join("");

            card.innerHTML = `
                <div>
                    <div class="flex justify-between items-start mb-2">
                        <div class="flex items-center gap-3">
                            <h3 class="font-display-lg text-headline-sm font-bold text-on-surface capitalize">${rec.name}</h3>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="flex items-center gap-1.5 px-2.5 py-1 bg-tertiary/10 border border-tertiary/30 rounded-lg">
                                <span class="material-symbols-outlined text-tertiary text-sm" style="font-variation-settings: 'FILL' 1;">star</span>
                                <span class="text-tertiary font-bold text-label-md">${rec.rating.toFixed(1)}</span>
                            </div>
                            <button class="p-2 bg-primary/20 border border-primary/30 text-primary rounded-xl remove-fav-btn" title="Remove Favorite">
                                <span class="material-symbols-outlined text-lg" style="font-variation-settings: 'FILL' 1;">favorite</span>
                            </button>
                        </div>
                    </div>

                    <div class="flex flex-wrap items-center gap-2 mt-3 mb-4">
                        ${cuisineHTML}
                        <span class="text-xs px-2.5 py-0.5 bg-primary/10 rounded-lg border border-primary/20 text-primary">
                            ${rec.estimated_cost}
                        </span>
                    </div>

                    <div class="p-4 bg-primary/5 border-l-4 border-primary rounded-r-xl italic text-body-md text-on-surface-variant relative mt-2 pl-8">
                        <span class="material-symbols-outlined absolute top-2 left-2 text-primary opacity-30 text-2xl">format_quote</span>
                        "${rec.explanation}"
                    </div>
                </div>
            `;

            card.querySelector(".remove-fav-btn").addEventListener("click", () => {
                const favIndex = favorites.findIndex(f => f.name.toLowerCase() === rec.name.toLowerCase());
                if (favIndex !== -1) {
                    favorites.splice(favIndex, 1);
                    localStorage.setItem("favorite_restaurants", JSON.stringify(favorites));
                    renderFavorites();
                }
            });

            grid.appendChild(card);
        });
    }

    // 9. Interactive Search Sorting & Filtering
    function setupSortingAndFiltering() {
        if (filterSearchInput) {
            filterSearchInput.addEventListener("input", (e) => {
                activeFilterQuery = e.target.value.toLowerCase().trim();
                applyFilterAndSort();
            });
        }

        if (sortSelect) {
            sortSelect.addEventListener("change", (e) => {
                activeSort = e.target.value;
                applyFilterAndSort();
            });
        }
    }

    function applyFilterAndSort() {
        if (!lastResultsData || !lastResultsData.recommendations) return;

        let filteredList = [...lastResultsData.recommendations];

        // 1. Apply Text Filter (match restaurant name or cuisine tags)
        if (activeFilterQuery) {
            filteredList = filteredList.filter(rec => 
                rec.name.toLowerCase().includes(activeFilterQuery) ||
                rec.cuisine.toLowerCase().includes(activeFilterQuery)
            );
        }

        // 2. Apply Sorting
        if (activeSort === "rating") {
            filteredList.sort((a, b) => b.rating - a.rating);
        } else if (activeSort === "cost-low") {
            // Extract numeric values from cost string, e.g. "₹500 for two" -> 500
            const getCostVal = (costStr) => {
                const matches = costStr.match(/\d+/);
                return matches ? parseInt(matches[0]) : 9999;
            };
            filteredList.sort((a, b) => getCostVal(a.estimated_cost) - getCostVal(b.estimated_cost));
        } else {
            // Default: Match Rank
            filteredList.sort((a, b) => a.rank - b.rank);
        }

        // 3. Render items
        resultsList.innerHTML = "";
        if (filteredList.length === 0) {
            resultsList.innerHTML = `
                <div class="p-6 bg-white/5 rounded-2xl text-center border border-white/5 text-on-surface-variant font-body-md">
                    No matching results found for "${activeFilterQuery}".
                </div>
            `;
        } else {
            filteredList.forEach(rec => {
                const card = buildRecommendationCard(rec, lastResultsData.metadata?.used_fallback);
                resultsList.appendChild(card);
            });
        }
    }

    // 10. Progressive Loader Animations
    let loadingInterval = null;
    function startProgressiveLoader() {
        const stepText = document.getElementById("loading-step-text");
        const loadingSteps = [
            "Connecting to Delhi restaurant directory...",
            "Scanning geographic sub-areas...",
            "Applying budget filter rules...",
            "Retrieving candidate pools...",
            "Activating Neural LLM Agent...",
            "Performing prompt instruction checks...",
            "Synthesizing ratings indicators...",
            "Compiling final recommendations graph..."
        ];

        let index = 0;
        if (stepText) stepText.textContent = loadingSteps[0];

        loadingInterval = setInterval(() => {
            index = (index + 1) % loadingSteps.length;
            if (stepText) stepText.textContent = loadingSteps[index];
        }, 1200);
    }

    function stopProgressiveLoader() {
        if (loadingInterval) {
            clearInterval(loadingInterval);
            loadingInterval = null;
        }
    }

    // 11. Submit search and fetch recommendations
    async function handleGenerate() {
        // Validate Inputs
        const location = locationSelect.value;
        const cuisine = cuisineSelect.value;

        if (!location) {
            showError("Please select a target city.");
            locationSelect.focus();
            return;
        }
        if (!cuisine) {
            showError("Please specify your preferred cuisine.");
            cuisineSelect.focus();
            return;
        }

        // Toggle UI states
        toggleFormInputs(false);
        showLoadingState();
        startProgressiveLoader();

        const payload = {
            location: location,
            budget: selectedBudget,
            cuisine: cuisine,
            min_rating: selectedRating,
            additional_preferences: additionalPrefs.value.trim() || null
        };

        try {
            const res = await fetch(`${API_BASE_URL}/api/v1/recommend`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();

            if (res.ok) {
                // Log payload to query history
                saveToHistory(payload, data);
                
                // Clear active filter text inputs on new load
                if (filterSearchInput) filterSearchInput.value = "";
                if (sortSelect) sortSelect.value = "rank";
                activeFilterQuery = "";
                activeSort = "rank";

                renderResults(data);
            } else {
                showError(data.detail || "An error occurred while generating recommendations.");
            }
        } catch (err) {
            console.error("Query failed:", err);
            showError("Could not connect to the recommendation server. Please check if your backend is running.");
        } finally {
            stopProgressiveLoader();
            toggleFormInputs(true);
        }
    }

    // Toggle forms enabled state
    function toggleFormInputs(enabled) {
        locationSelect.disabled = !enabled;
        cuisineSelect.disabled = !enabled;
        additionalPrefs.disabled = !enabled;
        generateBtn.disabled = !enabled;
        
        const budgetButtons = document.querySelectorAll(".budget-btn");
        budgetButtons.forEach(btn => {
            btn.disabled = !enabled;
        });

        const starButtons = document.querySelectorAll(".star-btn");
        starButtons.forEach(btn => {
            btn.disabled = !enabled;
        });
    }

    // State Switchers
    function showLoadingState() {
        emptyState.classList.add("hidden");
        resultsContainer.classList.add("hidden");
        errorBanner.classList.add("hidden");
        relaxationBanner.classList.add("hidden");
        loadingState.classList.remove("hidden");
    }

    function showError(msg) {
        loadingState.classList.add("hidden");
        emptyState.classList.add("hidden");
        resultsContainer.classList.add("hidden");
        
        errorMessage.textContent = msg;
        errorBanner.classList.remove("hidden");
        errorBanner.scrollIntoView({ behavior: "smooth" });
    }

    // Render results on success
    function renderResults(data) {
        loadingState.classList.add("hidden");
        emptyState.classList.add("hidden");
        errorBanner.classList.add("hidden");
        relaxationBanner.classList.add("hidden");

        // Save local copy of results for sorting/filtering
        lastResultsData = data;

        // 1. Process relaxation warning if any filters were dropped
        const metadata = data.metadata || {};
        if (metadata.filters_relaxed && metadata.filters_relaxed.length > 0) {
            const relaxedNames = metadata.filters_relaxed.map(f => f.replace("_", " "));
            relaxationMessage.textContent = `No exact matches found for all your criteria. We relaxed constraints on: "${relaxedNames.join(", ")}" to fetch the closest recommendations.`;
            relaxationBanner.classList.remove("hidden");
        }

        // 2. Set AI Summary Paragraph
        resultsSummaryText.textContent = data.summary || "Here are your curated recommendations.";

        // 3. Render Card List using current filters/sorting values
        applyFilterAndSort();

        resultsContainer.classList.remove("hidden");
        resultsContainer.scrollIntoView({ behavior: "smooth" });
    }

    // Construct recommendation card DOM element
    function buildRecommendationCard(rec, isFallback) {
        const cardDiv = document.createElement("div");
        cardDiv.className = "glass-card overflow-hidden rounded-2xl p-6 flex flex-col gap-4 relative transition-all";

        // Generate Cuisines list string or tags
        const cuisineTags = rec.cuisine.split(",").map(c => c.trim());
        const cuisineHTML = cuisineTags.map(c => `
            <span class="text-xs px-2.5 py-0.5 bg-white/5 rounded-lg border border-white/10 text-on-surface-variant capitalize">
                ${c}
            </span>
        `).join("");

        // Highlight fallback indicator if local rule ranker was used
        const fallbackBadge = isFallback ? `
            <span class="text-xs px-2 py-0.5 bg-amber-500/10 border border-amber-500/30 text-amber-500 rounded font-medium">
                Rule-Based Fallback
            </span>
        ` : "";

        // Check if item is favorited
        const isFav = isFavorite(rec.name);
        const favButtonClass = isFav 
            ? "p-2 bg-primary/20 border border-primary/30 text-primary rounded-xl transition-all fav-btn" 
            : "p-2 bg-white/5 border border-white/10 text-on-surface-variant hover:text-primary rounded-xl transition-all fav-btn";
        const favIconFill = isFav ? "1" : "0";

        cardDiv.innerHTML = `
            <div>
                <!-- Header Row -->
                <div class="flex justify-between items-start mb-2">
                    <div class="flex items-center gap-3 flex-wrap">
                        <span class="px-2.5 py-1 bg-primary/20 text-primary text-label-sm font-bold rounded-lg border border-primary/20">
                            #${rec.rank} RANK
                        </span>
                        <h3 class="font-display-lg text-headline-md font-bold text-on-surface capitalize">${rec.name}</h3>
                        ${fallbackBadge}
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="flex items-center gap-1.5 px-2.5 py-1 bg-tertiary/10 border border-tertiary/30 rounded-lg">
                            <span class="material-symbols-outlined text-tertiary text-sm" style="font-variation-settings: 'FILL' 1;">star</span>
                            <span class="text-tertiary font-bold text-label-md">${rec.rating.toFixed(1)}</span>
                        </div>
                        <button class="${favButtonClass}" title="Save Venue">
                            <span class="material-symbols-outlined text-lg" style="font-variation-settings: 'FILL' ${favIconFill};">favorite</span>
                        </button>
                    </div>
                </div>

                <!-- Attributes Row -->
                <div class="flex flex-wrap items-center gap-2 mt-3 mb-4">
                    ${cuisineHTML}
                    <span class="text-xs px-2.5 py-0.5 bg-primary/10 rounded-lg border border-primary/20 text-primary">
                        ${rec.estimated_cost}
                    </span>
                </div>

                <!-- Explanation Text -->
                <div class="p-4 bg-primary/5 border-l-4 border-primary rounded-r-xl italic text-body-md text-on-surface-variant relative mt-2 pl-8">
                    <span class="material-symbols-outlined absolute top-2 left-2 text-primary opacity-30 text-2xl">format_quote</span>
                    "${rec.explanation}"
                </div>
            </div>
        `;

        // Wire Favorite toggle event
        cardDiv.querySelector(".fav-btn").addEventListener("click", (e) => {
            const btn = e.currentTarget;
            toggleFavorite(rec, btn);
        });

        return cardDiv;
    }
});
