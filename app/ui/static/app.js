document.addEventListener("DOMContentLoaded", () => {
    // API Configuration: Set your Railway backend URL here in production
    const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
        ? ""
        : "https://restaurant-recommender-production.up.railway.app";

    // State management
    let selectedBudget = "medium";
    let selectedRating = 4.0;

    // DOM Elements
    const locationSelect = document.getElementById("location-select");
    const cuisineInput = document.getElementById("cuisine-input");
    const cuisinesDatalist = document.getElementById("cuisines-list");
    const additionalPrefs = document.getElementById("additional-preferences");
    const generateBtn = document.getElementById("generate-btn");
    
    // State Views
    const emptyState = document.getElementById("empty-state");
    const loadingState = document.getElementById("loading-state");
    const resultsContainer = document.getElementById("results-container");
    const resultsSummaryText = document.getElementById("results-summary-text");
    const resultsList = document.getElementById("results-list");
    const errorBanner = document.getElementById("error-banner");
    const errorMessage = document.getElementById("error-message");
    const relaxationBanner = document.getElementById("relaxation-banner");
    const relaxationMessage = document.getElementById("relaxation-message");

    // System Status elements
    const connectionDot = document.getElementById("connection-dot");
    const connectionText = document.getElementById("connection-text");
    const footerHealthDot = document.getElementById("footer-health-dot");
    const footerHealthText = document.getElementById("footer-health-text");

    // Initialize Page
    checkSystemHealth();
    loadMetadata();
    setupBudgetSelector();
    setupStarRating();

    // Event Listeners
    generateBtn.addEventListener("click", handleGenerate);

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
        const activeColor = "bg-tertiary";
        const inactiveColor = "bg-error";
        
        if (isHealthy) {
            connectionDot.className = `w-2 h-2 rounded-full ${activeColor} health-dot`;
            connectionText.textContent = text;
            connectionText.className = "text-label-sm font-label-sm text-tertiary tracking-wider uppercase";
            
            footerHealthDot.className = `w-1.5 h-1.5 ${activeColor} rounded-full`;
            footerHealthText.textContent = "healthy";
            footerHealthText.className = "font-medium text-tertiary";
        } else {
            connectionDot.className = `w-2 h-2 rounded-full ${inactiveColor} health-dot`;
            connectionText.textContent = text;
            connectionText.className = "text-label-sm font-label-sm text-error tracking-wider uppercase";
            
            footerHealthDot.className = `w-1.5 h-1.5 ${inactiveColor} rounded-full`;
            footerHealthText.textContent = "initializing";
            footerHealthText.className = "font-medium text-error";
        }
    }

    // 2. Fetch locations and cuisines to populate filter options
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

            // Load Cuisines
            const cuisRes = await fetch(`${API_BASE_URL}/api/v1/cuisines`);
            if (cuisRes.ok) {
                const cuisines = await cuisRes.json();
                cuisinesDatalist.innerHTML = "";
                cuisines.forEach(c => {
                    const opt = document.createElement("option");
                    opt.value = capitalizeString(c);
                    cuisinesDatalist.appendChild(opt);
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
                    // Reset styling to inactive state
                    b.className = "budget-btn py-3 px-4 rounded-xl border border-white/10 bg-white/5 text-on-surface hover:border-primary/50 transition-all font-label-md shadow-none";
                });
                
                // Set current selected budget
                selectedBudget = btn.getAttribute("data-budget");
                
                // Apply active styles
                btn.className = "budget-btn py-3 px-4 rounded-xl border-2 border-primary bg-primary/10 text-primary transition-all font-label-md shadow-[0_0_15px_rgba(192,193,255,0.2)]";
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

    // 5. Submit search and fetch recommendations
    async function handleGenerate() {
        // Validate Inputs
        const location = locationSelect.value;
        const cuisine = cuisineInput.value.trim();

        if (!location) {
            showError("Please select a target city.");
            locationSelect.focus();
            return;
        }
        if (!cuisine) {
            showError("Please specify your preferred cuisine.");
            cuisineInput.focus();
            return;
        }

        // Toggle UI states
        toggleFormInputs(false);
        showLoadingState();

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
                renderResults(data);
            } else {
                showError(data.detail || "An error occurred while generating recommendations.");
            }
        } catch (err) {
            console.error("Query failed:", err);
            showError("Could not connect to the recommendation server. Please check if uvicorn is running.");
        } finally {
            toggleFormInputs(true);
        }
    }

    // Toggle forms enabled state
    function toggleFormInputs(enabled) {
        locationSelect.disabled = !enabled;
        cuisineInput.disabled = !enabled;
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

        // 1. Process relaxation warning if any filters were dropped
        const metadata = data.metadata || {};
        if (metadata.filters_relaxed && metadata.filters_relaxed.length > 0) {
            const relaxedNames = metadata.filters_relaxed.map(f => f.replace("_", " "));
            relaxationMessage.textContent = `No exact matches found for all your criteria. We relaxed constraints on: "${relaxedNames.join(", ")}" to fetch the closest recommendations.`;
            relaxationBanner.classList.remove("hidden");
        }

        // 2. Set AI Summary Paragraph
        resultsSummaryText.textContent = data.summary || "Here are your curated recommendations.";

        // 3. Render Card List
        resultsList.innerHTML = "";
        
        if (!data.recommendations || data.recommendations.length === 0) {
            resultsList.innerHTML = `
                <div class="p-6 bg-white/5 rounded-2xl text-center border border-white/5 text-on-surface-variant font-body-md">
                    No recommendations found in the dataset.
                </div>
            `;
        } else {
            data.recommendations.forEach(rec => {
                const card = buildRecommendationCard(rec, metadata.used_fallback);
                resultsList.appendChild(card);
            });
        }

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
            <span class="text-label-sm px-2.5 py-0.5 bg-white/5 rounded-lg border border-white/10 text-on-surface-variant capitalize">
                ${c}
            </span>
        `).join("");

        // Highlight fallback indicator if local rule ranker was used
        const fallbackBadge = isFallback ? `
            <span class="text-xs px-2 py-0.5 bg-amber-500/10 border border-amber-500/30 text-amber-500 rounded font-medium">
                Rule-Based Fallback
            </span>
        ` : "";

        cardDiv.innerHTML = `
            <div>
                <!-- Header Row -->
                <div class="flex justify-between items-start mb-2">
                    <div class="flex items-center gap-3">
                        <span class="px-2.5 py-1 bg-primary/20 text-primary text-label-sm font-bold rounded-lg border border-primary/20">
                            #${rec.rank} RANK
                        </span>
                        <h3 class="font-display-lg text-headline-md font-bold text-on-surface capitalize">${rec.name}</h3>
                        ${fallbackBadge}
                    </div>
                    <div class="flex items-center gap-1.5 px-2.5 py-1 bg-tertiary/10 border border-tertiary/30 rounded-lg">
                        <span class="material-symbols-outlined text-tertiary text-sm" style="font-variation-settings: 'FILL' 1;">star</span>
                        <span class="text-tertiary font-bold text-label-md">${rec.rating.toFixed(1)}</span>
                    </div>
                </div>

                <!-- Attributes Row -->
                <div class="flex flex-wrap items-center gap-2 mt-3 mb-4">
                    ${cuisineHTML}
                    <span class="text-label-sm px-2.5 py-0.5 bg-primary/10 rounded-lg border border-primary/20 text-primary">
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

        return cardDiv;
    }
});
