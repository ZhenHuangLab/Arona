import { useState } from 'react';
import { ChevronDown, ChevronUp, Search, Sliders } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

interface GraphControlsProps {
  /** Available node types for filtering */
  nodeTypes: string[];
  /** Currently selected node types */
  selectedTypes: string[];
  /** Layout mode */
  layout: 'normal' | 'tight' | 'loose';
  /** Search query */
  searchQuery: string;
  /** Callback when node type selection changes */
  onTypeFilterChange: (types: string[]) => void;
  /** Callback when layout changes */
  onLayoutChange: (layout: 'normal' | 'tight' | 'loose') => void;
  /** Callback when search query changes */
  onSearchChange: (query: string) => void;
}

/**
 * GraphControls Component
 *
 * Control panel for graph visualization with:
 * - Layout selector (force simulation parameters)
 * - Node type filters (checkboxes)
 * - Search functionality
 *
 * Features:
 * - Collapsible panel design
 * - Minimalist UI with shadcn/ui components
 * - Real-time filtering and search
 */
export function GraphControls({
  nodeTypes,
  selectedTypes,
  layout,
  searchQuery,
  onTypeFilterChange,
  onLayoutChange,
  onSearchChange,
}: GraphControlsProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  /**
   * Handle checkbox toggle for node type filtering
   */
  const handleTypeToggle = (type: string) => {
    if (selectedTypes.includes(type)) {
      // Remove type from selection
      onTypeFilterChange(selectedTypes.filter(t => t !== type));
    } else {
      // Add type to selection
      onTypeFilterChange([...selectedTypes, type]);
    }
  };

  /**
   * Select all node types
   */
  const handleSelectAll = () => {
    onTypeFilterChange(nodeTypes);
  };

  /**
   * Deselect all node types
   */
  const handleDeselectAll = () => {
    onTypeFilterChange([]);
  };

  return (
    <Card className="p-4">
      {/* Header with toggle */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sliders className="h-5 w-5 text-muted-foreground" />
          <h3 className="text-sm font-semibold">Graph Controls</h3>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className="h-8 w-8 p-0"
        >
          {isExpanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
          <span className="sr-only">
            {isExpanded ? 'Collapse' : 'Expand'} controls
          </span>
        </Button>
      </div>

      {/* Collapsible content */}
      {isExpanded && (
        <div className="space-y-4">
          {/* Search */}
          <div className="space-y-2">
            <Label htmlFor="graph-search" className="text-sm font-medium">
              Search Nodes
            </Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                id="graph-search"
                type="text"
                placeholder="Search by node label..."
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>

          {/* Layout Selector */}
          <div className="space-y-2">
            <Label htmlFor="graph-layout" className="text-sm font-medium">
              Layout Density
            </Label>
            <Select value={layout} onValueChange={onLayoutChange}>
              <SelectTrigger id="graph-layout">
                <SelectValue placeholder="Select layout" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tight">Tight (High Density)</SelectItem>
                <SelectItem value="normal">Normal (Balanced)</SelectItem>
                <SelectItem value="loose">Loose (Low Density)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Adjust node spacing and force strength
            </p>
          </div>

          {/* Node Type Filters */}
          {nodeTypes.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium">Filter by Type</Label>
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleSelectAll}
                    className="h-7 text-xs"
                  >
                    All
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleDeselectAll}
                    className="h-7 text-xs"
                  >
                    None
                  </Button>
                </div>
              </div>
              <div className="space-y-2 max-h-48 overflow-y-auto border rounded-md p-3">
                {nodeTypes.map((type) => (
                  <div key={type} className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id={`type-${type}`}
                      checked={selectedTypes.includes(type)}
                      onChange={() => handleTypeToggle(type)}
                      className={cn(
                        'h-4 w-4 rounded border-gray-300',
                        'text-primary focus:ring-2 focus:ring-ring focus:ring-offset-2',
                        'cursor-pointer'
                      )}
                    />
                    <label
                      htmlFor={`type-${type}`}
                      className="text-sm font-normal cursor-pointer select-none"
                    >
                      {type}
                    </label>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                {selectedTypes.length} of {nodeTypes.length} types selected
              </p>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

