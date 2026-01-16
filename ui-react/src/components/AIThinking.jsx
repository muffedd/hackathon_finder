export default function AIThinking({ isVisible, currentStep }) {
    if (!isVisible) return null;

    const steps = [
        'Understanding your query...',
        'Searching hackathons...',
        'Analyzing matches...',
        'Generating recommendations...',
    ];

    return (
        <div className="ai-thinking" id="aiThinking">
            {steps.map((step, index) => (
                <div
                    key={index}
                    className={`thinking-step ${currentStep > index ? 'active' : ''} ${currentStep === index + 1 ? 'current' : ''}`}
                    data-step={index + 1}
                >
                    {step}
                </div>
            ))}
        </div>
    );
}
