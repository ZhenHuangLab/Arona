import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { QueryMode } from '@/types/chat';

interface ModeSelectorProps {
  value: QueryMode;
  onChange: (mode: QueryMode) => void;
  disabled?: boolean;
}

/**
 * Mode Selector Component
 *
 * Dropdown for selecting query mode (naive/local/global/hybrid).
 * Used in the chat input bar.
 */
export function ModeSelector({ value, onChange, disabled }: ModeSelectorProps) {
  return (
    <Select value={value} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger className="w-[140px]">
        <SelectValue placeholder="Select mode" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="naive">Naive</SelectItem>
        <SelectItem value="local">Local</SelectItem>
        <SelectItem value="global">Global</SelectItem>
        <SelectItem value="hybrid">Hybrid</SelectItem>
      </SelectContent>
    </Select>
  );
}
