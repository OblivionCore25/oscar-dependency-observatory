import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import TopRiskTable from './TopRiskTable';

const mockItems = Array.from({ length: 15 }, (_, i) => ({
  id: `pkg-${i}`,
  name: `package-${i}`,
  version: '1.0.0',
  ecosystem: 'npm',
  bottleneckScore: 1000 - i * 50,
  bottleneckPercentile: 95 - i,
  fanIn: 100 * i,
  fanOut: 50 * i,
  versionFanOut: 10 * i,
  pageRank: 0.05,
  closenessCentrality: 0.01,
}));

describe('TopRiskTable', () => {
  it('renders empty state correctly', () => {
    render(<TopRiskTable items={[]} />);
    expect(screen.getByText(/no high-risk dependencies found/i)).toBeInTheDocument();
  });

  it('renders initial list of 10 items', () => {
    render(
      <BrowserRouter>
        <TopRiskTable items={mockItems} />
      </BrowserRouter>
    );
    
    // Default page size is 10
    expect(screen.getByText('package-0')).toBeInTheDocument();
    expect(screen.getByText('package-9')).toBeInTheDocument();
    // Item 11 should not be visible yet
    expect(screen.queryByText('package-10')).not.toBeInTheDocument();
  });

  it('handles pagination next and previous', () => {
    render(
      <BrowserRouter>
        <TopRiskTable items={mockItems} />
      </BrowserRouter>
    );
    
    const nextBtn = screen.getByTitle('Next Page');
    fireEvent.click(nextBtn);
    
    // Page 2
    expect(screen.getByText('package-10')).toBeInTheDocument();
    expect(screen.getByText('package-14')).toBeInTheDocument();
    expect(screen.queryByText('package-0')).not.toBeInTheDocument();

    const prevBtn = screen.getByTitle('Previous Page');
    fireEvent.click(prevBtn);
    
    // Back to page 1
    expect(screen.getByText('package-0')).toBeInTheDocument();
    expect(screen.queryByText('package-10')).not.toBeInTheDocument();
  });

  it('handles page size change', () => {
    render(
      <BrowserRouter>
        <TopRiskTable items={mockItems} />
      </BrowserRouter>
    );
    
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: '20' } });
    
    // Now all 15 should be visible since page size is 20
    expect(screen.getByText('package-0')).toBeInTheDocument();
    expect(screen.getByText('package-14')).toBeInTheDocument();
  });
});
