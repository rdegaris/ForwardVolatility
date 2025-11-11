/**
 * Forward Volatility / Forward Factor Calculator Component
 * 
 * Calculates forward volatility and forward factor between two option expiration dates.
 * Matches the desktop calculator.py functionality.
 */

import React, { useState } from 'react';

interface CalculatorState {
  frontIV: string;
  backIV: string;
  frontDate: string;
  backDate: string;
}

interface CalculatorResults {
  forwardVol: number;
  forwardFactor: number;
  frontDTE: number;
  backDTE: number;
  dateRange: string;
}

const ForwardVolatilityCalculator: React.FC = () => {
  const [inputs, setInputs] = useState<CalculatorState>({
    frontIV: '',
    backIV: '',
    frontDate: '',
    backDate: ''
  });

  const [results, setResults] = useState<CalculatorResults | null>(null);
  const [error, setError] = useState<string>('');

  // Calculate DTE from a date string
  const calculateDTE = (dateStr: string): number => {
    const targetDate = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diffTime = targetDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  // Format date for display
  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    });
  };

  // Calculate forward volatility and forward factor
  const calculate = () => {
    setError('');
    
    try {
      // Validate inputs
      const frontIV = parseFloat(inputs.frontIV);
      const backIV = parseFloat(inputs.backIV);
      
      if (isNaN(frontIV) || isNaN(backIV)) {
        setError('Please enter valid IV values');
        return;
      }

      if (frontIV <= 0 || frontIV > 1000 || backIV <= 0 || backIV > 1000) {
        setError('IV must be between 1 and 1000');
        return;
      }

      if (!inputs.frontDate || !inputs.backDate) {
        setError('Please select both dates');
        return;
      }

      const frontDTE = calculateDTE(inputs.frontDate);
      const backDTE = calculateDTE(inputs.backDate);

      if (frontDTE <= 0 || backDTE <= 0) {
        setError('Dates must be in the future');
        return;
      }

      if (frontDTE >= backDTE) {
        setError('Front date must be before back date');
        return;
      }

      // Convert to decimal (IV is input as percentage)
      const sigma1 = frontIV / 100;
      const sigma2 = backIV / 100;

      // Convert DTE to years
      const T1 = frontDTE / 365;
      const T2 = backDTE / 365;

      // Calculate forward variance
      const forwardVariance = (sigma2 * sigma2 * T2 - sigma1 * sigma1 * T1) / (T2 - T1);

      if (forwardVariance < 0) {
        setError('Negative forward variance - front IV too high or back IV too low');
        return;
      }

      // Calculate forward volatility
      const forwardVol = Math.sqrt(forwardVariance);

      // Calculate forward factor: (Front IV - Forward Vol) / Forward Vol
      const forwardFactor = (sigma1 - forwardVol) / forwardVol;

      setResults({
        forwardVol: forwardVol * 100, // Convert back to percentage
        forwardFactor: forwardFactor * 100, // As percentage
        frontDTE,
        backDTE,
        dateRange: `${formatDate(inputs.frontDate)} and ${formatDate(inputs.backDate)}`
      });
    } catch (err) {
      setError('Calculation error: ' + (err as Error).message);
    }
  };

  const handleInputChange = (field: keyof CalculatorState, value: string) => {
    setInputs(prev => ({ ...prev, [field]: value }));
    setResults(null); // Clear results when inputs change
  };

  return (
    <div className="forward-volatility-calculator">
      <div className="calculator-header">
        <h2>Forward Volatility / Forward Factor Calculator</h2>
        <p className="calculator-subtitle">
          Calculate forward volatility and forward factor between two dates
        </p>
      </div>

      <div className="calculator-body">
        <div className="inputs-section">
          <h3>Inputs</h3>
          
          <div className="input-grid">
            {/* Front IV */}
            <div className="input-group">
              <label htmlFor="frontIV">Front IV (%)</label>
              <input
                id="frontIV"
                type="number"
                step="0.01"
                min="1"
                max="1000"
                value={inputs.frontIV}
                onChange={(e) => handleInputChange('frontIV', e.target.value)}
                placeholder="61.87"
              />
              <span className="input-hint">IV in percent (1-1000)</span>
            </div>

            {/* Back IV */}
            <div className="input-group">
              <label htmlFor="backIV">Back IV (%)</label>
              <input
                id="backIV"
                type="number"
                step="0.01"
                min="1"
                max="1000"
                value={inputs.backIV}
                onChange={(e) => handleInputChange('backIV', e.target.value)}
                placeholder="52.11"
              />
              <span className="input-hint">IV in percent (1-1000)</span>
            </div>

            {/* Front Date */}
            <div className="input-group">
              <label htmlFor="frontDate">Front Date</label>
              <input
                id="frontDate"
                type="date"
                value={inputs.frontDate}
                onChange={(e) => handleInputChange('frontDate', e.target.value)}
              />
              {inputs.frontDate && (
                <span className="input-hint">
                  {calculateDTE(inputs.frontDate)} DTE
                </span>
              )}
            </div>

            {/* Back Date */}
            <div className="input-group">
              <label htmlFor="backDate">Back Date</label>
              <input
                id="backDate"
                type="date"
                value={inputs.backDate}
                onChange={(e) => handleInputChange('backDate', e.target.value)}
              />
              {inputs.backDate && (
                <span className="input-hint">
                  {calculateDTE(inputs.backDate)} DTE
                </span>
              )}
            </div>
          </div>

          <button 
            className="calculate-button"
            onClick={calculate}
          >
            Calculate
          </button>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {results && (
          <div className="results-section">
            <h3>Results</h3>
            
            <div className="results-grid">
              <div className="result-card">
                <h4>Forward Volatility</h4>
                <div className="result-value">
                  {results.forwardVol.toFixed(2)}%
                </div>
                <div className="result-subtitle">
                  Between {results.dateRange}
                </div>
              </div>

              <div className="result-card">
                <h4>Forward Factor</h4>
                <div className={`result-value ${results.forwardFactor > 0 ? 'positive' : 'negative'}`}>
                  {results.forwardFactor > 0 ? '+' : ''}{results.forwardFactor.toFixed(2)}%
                </div>
                <div className="result-subtitle">
                  (Front IV / Forward Vol) - 1
                </div>
              </div>
            </div>

            <div className="calculation-details">
              <h4>Calculation Details</h4>
              <div className="detail-row">
                <span>Front DTE:</span>
                <span>{results.frontDTE} days</span>
              </div>
              <div className="detail-row">
                <span>Back DTE:</span>
                <span>{results.backDTE} days</span>
              </div>
              <div className="detail-row">
                <span>Time Spread:</span>
                <span>{results.backDTE - results.frontDTE} days</span>
              </div>
              <div className="detail-row">
                <span>Front IV:</span>
                <span>{inputs.frontIV}%</span>
              </div>
              <div className="detail-row">
                <span>Back IV:</span>
                <span>{inputs.backIV}%</span>
              </div>
              <div className="detail-row">
                <span>Forward Volatility:</span>
                <span>{results.forwardVol.toFixed(2)}%</span>
              </div>
            </div>

            <div className="interpretation">
              <h4>Interpretation</h4>
              {results.forwardFactor > 40 ? (
                <p className="bullish">
                  ✅ <strong>Strong Opportunity:</strong> Forward Factor above 40% indicates front-month IV is significantly elevated. 
                  Consider calendar spreads to capture the volatility term structure edge.
                </p>
              ) : results.forwardFactor > 20 ? (
                <p className="moderate">
                  ⚠️ <strong>Moderate Opportunity:</strong> Forward Factor above 20% suggests a potential calendar spread opportunity.
                  Front-month IV is elevated relative to forward volatility.
                </p>
              ) : results.forwardFactor > 0 ? (
                <p className="neutral">
                  📊 <strong>Positive FF:</strong> Front IV is higher than forward vol, but the edge may be small.
                  Consider other factors before entering a trade.
                </p>
              ) : (
                <p className="bearish">
                  ❌ <strong>Negative FF:</strong> Front IV is lower than forward volatility. 
                  Calendar spreads are not favorable in this term structure.
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .forward-volatility-calculator {
          max-width: 1200px;
          margin: 0 auto;
          padding: 2rem;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .calculator-header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .calculator-header h2 {
          font-size: 2rem;
          font-weight: 700;
          margin-bottom: 0.5rem;
          color: #1a1a1a;
        }

        .calculator-subtitle {
          font-size: 1rem;
          color: #666;
        }

        .calculator-body {
          background: #ffffff;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
          padding: 2rem;
        }

        .inputs-section h3,
        .results-section h3 {
          font-size: 1.5rem;
          font-weight: 600;
          margin-bottom: 1.5rem;
          color: #1a1a1a;
        }

        .input-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1.5rem;
          margin-bottom: 2rem;
        }

        .input-group {
          display: flex;
          flex-direction: column;
        }

        .input-group label {
          font-weight: 600;
          margin-bottom: 0.5rem;
          color: #333;
          font-size: 0.9rem;
        }

        .input-group input {
          padding: 0.75rem;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          font-size: 1.1rem;
          transition: border-color 0.2s;
        }

        .input-group input:focus {
          outline: none;
          border-color: #4CAF50;
        }

        .input-hint {
          font-size: 0.8rem;
          color: #666;
          margin-top: 0.25rem;
        }

        .calculate-button {
          background: #4CAF50;
          color: white;
          border: none;
          padding: 1rem 3rem;
          font-size: 1.1rem;
          font-weight: 600;
          border-radius: 8px;
          cursor: pointer;
          transition: background 0.2s;
          display: block;
          margin: 0 auto;
        }

        .calculate-button:hover {
          background: #45a049;
        }

        .error-message {
          background: #ffebee;
          color: #c62828;
          padding: 1rem;
          border-radius: 8px;
          margin: 1.5rem 0;
          border-left: 4px solid #c62828;
        }

        .results-section {
          margin-top: 2rem;
          padding-top: 2rem;
          border-top: 2px solid #f0f0f0;
        }

        .results-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 1.5rem;
          margin-bottom: 2rem;
        }

        .result-card {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .result-card h4 {
          font-size: 1rem;
          font-weight: 600;
          margin-bottom: 0.5rem;
          opacity: 0.9;
        }

        .result-value {
          font-size: 2.5rem;
          font-weight: 700;
          margin: 0.5rem 0;
        }

        .result-value.positive {
          color: #4CAF50;
        }

        .result-value.negative {
          color: #f44336;
        }

        .result-subtitle {
          font-size: 0.85rem;
          opacity: 0.8;
        }

        .calculation-details {
          background: #f9f9f9;
          padding: 1.5rem;
          border-radius: 8px;
          margin-bottom: 1.5rem;
        }

        .calculation-details h4 {
          font-size: 1.1rem;
          font-weight: 600;
          margin-bottom: 1rem;
          color: #1a1a1a;
        }

        .detail-row {
          display: flex;
          justify-content: space-between;
          padding: 0.5rem 0;
          border-bottom: 1px solid #e0e0e0;
        }

        .detail-row:last-child {
          border-bottom: none;
          font-weight: 600;
        }

        .interpretation {
          background: #f0f7ff;
          padding: 1.5rem;
          border-radius: 8px;
          border-left: 4px solid #2196F3;
        }

        .interpretation h4 {
          font-size: 1.1rem;
          font-weight: 600;
          margin-bottom: 0.75rem;
          color: #1a1a1a;
        }

        .interpretation p {
          line-height: 1.6;
          margin: 0;
        }

        .bullish {
          color: #2e7d32;
        }

        .moderate {
          color: #f57c00;
        }

        .neutral {
          color: #1976d2;
        }

        .bearish {
          color: #c62828;
        }

        @media (max-width: 768px) {
          .input-grid {
            grid-template-columns: 1fr;
          }

          .results-grid {
            grid-template-columns: 1fr;
          }

          .result-value {
            font-size: 2rem;
          }
        }
      `}</style>
    </div>
  );
};

export default ForwardVolatilityCalculator;
