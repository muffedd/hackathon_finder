import { useState, useCallback } from 'react';
import { aiSearch } from '../utils/api';

export function useAISearch() {
    const [isSearching, setIsSearching] = useState(false);
    const [currentStep, setCurrentStep] = useState(0);
    const [results, setResults] = useState(null);
    const [query, setQuery] = useState('');
    const [error, setError] = useState(null);

    const search = useCallback(async (searchQuery) => {
        if (!searchQuery.trim()) return;

        setQuery(searchQuery);
        setIsSearching(true);
        setError(null);
        setResults(null);

        // Thinking steps animation
        const steps = [1, 2, 3, 4];
        for (const step of steps) {
            setCurrentStep(step);
            await new Promise(resolve => setTimeout(resolve, 600));
        }

        try {
            const data = await aiSearch(searchQuery);
            setResults(data.results || []);
        } catch (err) {
            setError(err.message);
            console.error('AI search failed:', err);
        } finally {
            setIsSearching(false);
            setCurrentStep(0);
        }
    }, []);

    const clearResults = useCallback(() => {
        setResults(null);
        setQuery('');
        setError(null);
    }, []);

    return {
        search,
        isSearching,
        currentStep,
        results,
        query,
        error,
        clearResults,
    };
}
