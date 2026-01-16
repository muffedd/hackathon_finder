import { formatPrize } from '../utils/formatters';

export default function AIResults({ results, query }) {
    if (!results || results.length === 0) return null;

    return (
        <div className="ai-results" id="aiResults">
            <div className="ai-results-header">
                <h3>AI Recommendations</h3>
                <p className="ai-query-echo">For: "{query}"</p>
            </div>
            <div className="ai-results-grid">
                {results.slice(0, 4).map((result, index) => (
                    <a
                        key={result.id || index}
                        href={result.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ai-result-card"
                    >
                        <div className="ai-result-match">
                            {Math.round(result.score * 100)}% Match
                        </div>
                        <h4 className="ai-result-title">{result.title}</h4>
                        {result.reason && (
                            <p className="ai-result-reason">{result.reason}</p>
                        )}
                        <div className="ai-result-meta">
                            {result.prize_pool && (
                                <span className="ai-result-prize">{formatPrize(result.prize_pool)}</span>
                            )}
                            {result.source && (
                                <span className="ai-result-source">{result.source}</span>
                            )}
                        </div>
                    </a>
                ))}
            </div>
        </div>
    );
}
