"use client";

import React from 'react';

export interface DataTableColumn<T = any> {
  /** Column header text */
  header: string;
  /** Accessor key for the data */
  accessor: keyof T | string;
  /** Custom render function for cell content */
  render?: (value: any, row: T, index: number) => React.ReactNode;
  /** Column width className */
  width?: string;
  /** Text alignment */
  align?: 'left' | 'center' | 'right';
}

export interface DataTableProps<T = any> {
  /** Array of data objects to display */
  data: T[];
  /** Column configuration */
  columns: DataTableColumn<T>[];
  /** Optional loading state */
  loading?: boolean;
  /** Optional empty state message */
  emptyMessage?: string;
  /** Striped rows */
  striped?: boolean;
  /** Hoverable rows */
  hoverable?: boolean;
  /** Additional className for table */
  className?: string;
}

/**
 * DataTable Organism Component
 * 
 * A flexible and feature-rich table component for displaying structured data.
 * Supports custom rendering, alignment, and responsive styling.
 * 
 * Features:
 * - Dark mode support
 * - Custom cell rendering
 * - Column alignment control
 * - Loading and empty states
 * - Striped and hoverable rows
 * - Responsive design
 * - Type-safe with generics
 * 
 * @example
 * ```tsx
 * interface Product {
 *   id: string;
 *   name: string;
 *   price: number;
 *   stock: number;
 * }
 * 
 * const columns: DataTableColumn<Product>[] = [
 *   {
 *     header: 'Product',
 *     accessor: 'name',
 *   },
 *   {
 *     header: 'Price',
 *     accessor: 'price',
 *     render: (value) => `$${value.toFixed(2)}`,
 *     align: 'right',
 *   },
 *   {
 *     header: 'Stock',
 *     accessor: 'stock',
 *     render: (value) => (
 *       <Badge variant={value > 0 ? 'success' : 'danger'}>
 *         {value > 0 ? 'In Stock' : 'Out of Stock'}
 *       </Badge>
 *     ),
 *     align: 'center',
 *   },
 * ];
 * 
 * <DataTable
 *   data={products}
 *   columns={columns}
 *   hoverable
 *   striped
 * />
 * 
 * // With custom rendering
 * <DataTable
 *   data={users}
 *   columns={[
 *     {
 *       header: 'User',
 *       accessor: 'name',
 *       render: (value, row) => (
 *         <div className="flex items-center gap-2">
 *           <Avatar src={row.avatar} size="sm" />
 *           <span>{value}</span>
 *         </div>
 *       ),
 *     },
 *     {
 *       header: 'Status',
 *       accessor: 'status',
 *       render: (value) => (
 *         <Badge variant={value === 'active' ? 'success' : 'secondary'}>
 *           {value}
 *         </Badge>
 *       ),
 *     },
 *   ]}
 *   emptyMessage="No users found"
 * />
 * ```
 */
export function DataTable<T = any>({
  data,
  columns,
  loading = false,
  emptyMessage = 'No data available',
  striped = false,
  hoverable = true,
  className = '',
}: DataTableProps<T>) {
  const getNestedValue = (obj: any, path: string) => {
    return path.split('.').reduce((acc, part) => acc?.[part], obj);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500 dark:text-gray-400">{emptyMessage}</div>
      </div>
    );
  }

  return (
    <div className={`w-full overflow-x-auto ${className}`}>
      <table className="w-full text-sm text-left table-auto">
        <thead>
          <tr>
            {columns.map((column, index) => (
              <th
                key={index}
                className={`px-3 py-2 text-xs font-medium tracking-wider uppercase border-b border-gray-100 dark:border-gray-800 leading-4 text-gray-700 dark:text-gray-300 ${
                  column.align === 'center'
                    ? 'text-center'
                    : column.align === 'right'
                    ? 'text-right'
                    : 'text-left'
                } ${column.width || ''}`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              className={`
                border-b border-gray-100 dark:border-gray-800
                ${striped && rowIndex % 2 === 1 ? 'bg-gray-50 dark:bg-gray-900' : ''}
                ${hoverable ? 'hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors' : ''}
              `}
            >
              {columns.map((column, colIndex) => {
                const value = getNestedValue(row, column.accessor as string);
                const content = column.render
                  ? column.render(value, row, rowIndex)
                  : value;

                return (
                  <td
                    key={colIndex}
                    className={`px-3 py-2 whitespace-nowrap ${
                      column.align === 'center'
                        ? 'text-center'
                        : column.align === 'right'
                        ? 'text-right'
                        : 'text-left'
                    }`}
                  >
                    {content}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

DataTable.displayName = 'DataTable';

export default DataTable;
