import { useState } from 'react';
import AIThinking from './AIThinking';
import AIResults from './AIResults';

export default function Hero({ onSearch, isSearching, currentStep, results, query }) {
    const [inputValue, setInputValue] = useState('');

    const handleSubmit = (e) => {
        e?.preventDefault();
        if (inputValue.trim()) {
            onSearch(inputValue.trim());
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') {
            handleSubmit();
        }
    };

    return (
        <section className="hero">
            <div className="hero-content">
                <h1 className="hero-title">Find Your Next <span className="gradient-text">Hackathon</span></h1>
                <p className="hero-subtitle">
                    AI-powered search across <span id="platformCount">12</span>+ platforms. Real-time updates from Unstop, Devpost, Devfolio & more.
                </p>

                {/* AI Search Box */}
                <div className="ai-search-container">
                    <div className="ai-search-inner">
                        <input
                            type="text"
                            className="ai-search-input"
                            id="aiSearchInput"
                            placeholder="e.g., beginner friendly hackathons in India with prizes"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyPress={handleKeyPress}
                        />
                        <button
                            className="ai-search-btn"
                            id="aiSearchBtn"
                            onClick={handleSubmit}
                            disabled={isSearching}
                        >
                            Ask AI
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
                                <path d="M5 12h14M12 5l7 7-7 7" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* AI Thinking Process */}
                <AIThinking isVisible={isSearching} currentStep={currentStep} />

                {/* AI Results */}
                <AIResults results={results} query={query} />
            </div>
        </section>
    );
}
