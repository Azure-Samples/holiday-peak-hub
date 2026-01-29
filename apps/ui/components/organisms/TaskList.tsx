"use client";

import React, { useReducer, useState } from 'react';
import { FiX, FiPlus } from 'react-icons/fi';
import { Badge } from '../atoms/Badge';
import { Input } from '../atoms/Input';
import { Button } from '../atoms/Button';
import { Checkbox } from '../atoms/Checkbox';

export interface TaskItem {
  /** Unique task ID */
  id: string | number;
  /** Task title/description */
  title: string;
  /** Completion status */
  completed: boolean;
  /** Optional category/label */
  category?: string;
  /** Optional priority/status badge */
  badge?: {
    label: string;
    variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info' | 'light';
  };
  /** Optional avatar/assignee image */
  avatar?: string;
  /** Optional due date or timestamp */
  date?: string;
}

export interface TaskListProps {
  /** Initial tasks */
  initialTasks?: TaskItem[];
  /** Allow adding new tasks */
  allowAdd?: boolean;
  /** Allow removing tasks */
  allowRemove?: boolean;
  /** Show completed task count */
  showStats?: boolean;
  /** Allow clearing completed tasks */
  allowClearCompleted?: boolean;
  /** Placeholder for add input */
  addPlaceholder?: string;
  /** Callback when tasks change */
  onChange?: (tasks: TaskItem[]) => void;
  /** Additional className */
  className?: string;
}

type TaskAction =
  | { type: 'ADD'; title: string }
  | { type: 'REMOVE'; id: string | number }
  | { type: 'TOGGLE'; id: string | number }
  | { type: 'CLEAR_COMPLETED' }
  | { type: 'CLEAR_ALL' };

/**
 * TaskList Organism Component
 * 
 * A complete task management component with add, remove, toggle, and filter functionality.
 * Perfect for to-do lists, task boards, and project management interfaces.
 * 
 * Features:
 * - Dark mode support
 * - Add new tasks
 * - Remove individual tasks
 * - Toggle completion status
 * - Clear completed tasks
 * - Task counter
 * - Optional categories and badges
 * - Avatar support for assignees
 * - Due dates/timestamps
 * 
 * @example
 * ```tsx
 * // Basic task list
 * <TaskList
 *   initialTasks={[
 *     { id: 1, title: 'Complete project proposal', completed: false },
 *     { id: 2, title: 'Review pull requests', completed: true },
 *   ]}
 *   allowAdd
 *   allowRemove
 *   showStats
 * />
 * 
 * // Advanced with categories and badges
 * <TaskList
 *   initialTasks={[
 *     {
 *       id: 1,
 *       title: 'Fix authentication bug',
 *       completed: false,
 *       category: 'Development',
 *       badge: { label: 'High Priority', variant: 'danger' },
 *       avatar: '/images/john.jpg',
 *       date: 'Due today',
 *     },
 *     {
 *       id: 2,
 *       title: 'Update documentation',
 *       completed: false,
 *       category: 'Documentation',
 *       badge: { label: 'Low', variant: 'success' },
 *       avatar: '/images/jane.jpg',
 *       date: 'Due tomorrow',
 *     },
 *   ]}
 *   allowAdd
 *   allowRemove
 *   showStats
 *   allowClearCompleted
 *   onChange={(tasks) => console.log('Tasks updated:', tasks)}
 * />
 * ```
 */
export const TaskList: React.FC<TaskListProps> = ({
  initialTasks = [],
  allowAdd = true,
  allowRemove = true,
  showStats = true,
  allowClearCompleted = true,
  addPlaceholder = 'Add new task...',
  onChange,
  className = '',
}) => {
  const taskReducer = (state: TaskItem[], action: TaskAction): TaskItem[] => {
    let newState: TaskItem[];
    
    switch (action.type) {
      case 'ADD':
        newState = [
          ...state,
          {
            id: Date.now(),
            title: action.title,
            completed: false,
          },
        ];
        break;
      case 'REMOVE':
        newState = state.filter((task) => task.id !== action.id);
        break;
      case 'TOGGLE':
        newState = state.map((task) =>
          task.id === action.id ? { ...task, completed: !task.completed } : task
        );
        break;
      case 'CLEAR_COMPLETED':
        newState = state.filter((task) => !task.completed);
        break;
      case 'CLEAR_ALL':
        newState = [];
        break;
      default:
        return state;
    }
    
    onChange?.(newState);
    return newState;
  };

  const [tasks, dispatch] = useReducer(taskReducer, initialTasks);
  const [inputValue, setInputValue] = useState('');

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      dispatch({ type: 'ADD', title: inputValue.trim() });
      setInputValue('');
    }
  };

  const activeTasks = tasks.filter((t) => !t.completed);
  const completedTasks = tasks.filter((t) => t.completed);

  return (
    <div className={`flex flex-col w-full space-y-4 ${className}`}>
      {/* Task List */}
      <div className="space-y-2">
        {tasks.map((task) => (
          <div
            key={task.id}
            className="flex items-center gap-4 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            {/* Checkbox */}
            <Checkbox
              checked={task.completed}
              onChange={() => dispatch({ type: 'TOGGLE', id: task.id })}
            />

            {/* Avatar */}
            {task.avatar && (
              <img
                src={task.avatar}
                alt={task.title}
                className="w-8 h-8 rounded-full object-cover flex-shrink-0"
              />
            )}

            {/* Task Content */}
            <div className={`flex-1 min-w-0 ${task.completed ? 'line-through opacity-60' : ''}`}>
              <div className="text-sm font-semibold truncate">{task.title}</div>
              {task.category && (
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {task.category}
                </div>
              )}
              {task.badge && (
                <Badge
                  variant={task.badge.variant || 'secondary'}
                  size="sm"
                  className="mt-1"
                >
                  {task.badge.label}
                </Badge>
              )}
            </div>

            {/* Date */}
            {task.date && (
              <div className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap flex-shrink-0">
                {task.date}
              </div>
            )}

            {/* Remove Button */}
            {allowRemove && (
              <button
                onClick={() => dispatch({ type: 'REMOVE', id: task.id })}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors flex-shrink-0"
                aria-label="Remove task"
              >
                <FiX size={18} />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Add Task Form */}
      {allowAdd && (
        <form onSubmit={handleAdd} className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={addPlaceholder}
            className="flex-1"
          />
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={!inputValue.trim()}
          >
            <FiPlus size={18} />
          </Button>
        </form>
      )}

      {/* Stats and Actions */}
      {showStats && tasks.length > 0 && (
        <div className="flex items-center justify-between pt-2 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm font-semibold text-gray-700 dark:text-gray-300">
            {activeTasks.length} {activeTasks.length === 1 ? 'task' : 'tasks'} left
          </div>

          <div className="flex gap-2">
            {allowClearCompleted && completedTasks.length > 0 && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => dispatch({ type: 'CLEAR_COMPLETED' })}
              >
                Clear completed
              </Button>
            )}
            <Button
              variant="secondary"
              size="sm"
              onClick={() => dispatch({ type: 'CLEAR_ALL' })}
            >
              Clear all
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

TaskList.displayName = 'TaskList';

export default TaskList;
