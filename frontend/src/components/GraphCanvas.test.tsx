import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import GraphCanvas from './GraphCanvas';

let cyCallbacks: Record<string, Function> = {};
let mockElements = { removeClass: vi.fn() };
let exposedCy: any;

vi.mock('react-cytoscapejs', () => ({
  default: ({ cy }: any) => {
    if (cy) {
      exposedCy = {
        on: (event: string, selectorOrHandler: any, handler?: any) => {
          if (handler) {
            cyCallbacks[`${event}_${selectorOrHandler}`] = handler;
          } else {
            cyCallbacks[event] = selectorOrHandler;
          }
        },
        elements: () => mockElements,
      };
      cy(exposedCy);
    }
    return <div data-testid="cytoscape-mock">Cytoscape Content</div>;
  }
}));

describe('GraphCanvas', () => {
  beforeEach(() => {
    cyCallbacks = {};
    mockElements.removeClass.mockClear();
  });

  const mockData = {
    root: 'A',
    nodes: [
      { id: 'A', package: 'react', version: '18.2.0', label: 'react 18' },
      { id: 'B', package: 'js-tokens', version: '4.0.0' },
      { id: 'C', package: 'lodash', version: '4.17.21' }
    ],
    edges: [
      { source: 'A', target: 'B', constraint: '^4.0.0' },
      { source: 'B', target: 'C', constraint: 'unconstrained' },
      { source: 'A', target: 'C', constraint: '==1.0.0' }
    ]
  };

  it('processes transitive graph data and renders elements without crashing', () => {
    const { getByTestId } = render(<GraphCanvas data={mockData as any} />);
    expect(getByTestId('cytoscape-mock')).toBeInTheDocument();
  });

  it('handles edge interactions spanning hovers, taps, and tooltips', () => {
    const mockOnEdgeSelect = vi.fn();
    render(<GraphCanvas data={mockData as any} onEdgeSelect={mockOnEdgeSelect} />);
    
    // Simulate edge mouseover
    const mockEvt = {
      target: {
        data: (key: string) => mockData.edges[0][key as keyof typeof mockData.edges[0]],
        addClass: vi.fn(),
        removeClass: vi.fn()
      },
      renderedPosition: { x: 100, y: 150 }
    };

    // Trigger hover (mouseover)
    act(() => cyCallbacks['mouseover_edge']?.(mockEvt));
    expect(mockEvt.target.addClass).toHaveBeenCalledWith('hovered');
    expect(screen.getByText('^4.0.0')).toBeInTheDocument(); // Shows the constraint text
    expect(screen.getByText('Range Bounded ✓')).toBeInTheDocument();

    // Trigger mouseout
    act(() => cyCallbacks['mouseout_edge']?.(mockEvt));
    expect(mockEvt.target.removeClass).toHaveBeenCalledWith('hovered');
    expect(screen.queryByText('^4.0.0')).not.toBeInTheDocument();

    // Test pinning (tap on edge)
    act(() => cyCallbacks['tap_edge']?.(mockEvt));
    expect(mockElements.removeClass).toHaveBeenCalledWith('hovered');
    expect(mockEvt.target.addClass).toHaveBeenCalledWith('hovered');
    expect(screen.getByText('^4.0.0')).toBeInTheDocument();
    expect(mockOnEdgeSelect).toHaveBeenCalledWith({ source: 'A', target: 'B' });

    // Test different severity badge formats
    const mockUnconstrainedEvt = { ...mockEvt, target: { ...mockEvt.target, data: (key: string) => mockData.edges[1][key as keyof typeof mockData.edges[1]] } };
    act(() => cyCallbacks['tap_edge']?.(mockUnconstrainedEvt));
    expect(screen.getByText('unconstrained')).toBeInTheDocument();
    expect(screen.getByText('Unconstrained ⚠️')).toBeInTheDocument();

    const mockExactEvt = { ...mockEvt, target: { ...mockEvt.target, data: (key: string) => mockData.edges[2][key as keyof typeof mockData.edges[2]] } };
    act(() => cyCallbacks['tap_edge']?.(mockExactEvt));
    expect(screen.getByText('==1.0.0')).toBeInTheDocument();
    expect(screen.getByText('Pinned 🔒')).toBeInTheDocument();

    // Dismiss by tapping background
    act(() => cyCallbacks['tap']?.({ target: exposedCy })); // Simulate tapping cy itself
    expect(mockElements.removeClass).toHaveBeenCalledWith('hovered');
    expect(screen.queryByText('==1.0.0')).not.toBeInTheDocument();
    expect(mockOnEdgeSelect).toHaveBeenCalledWith(null);

    // Pan/Zoom clears tooltip
    act(() => cyCallbacks['tap_edge']?.(mockExactEvt));
    act(() => cyCallbacks['pan zoom']?.());
    expect(screen.queryByText('==1.0.0')).not.toBeInTheDocument();
  });
});
