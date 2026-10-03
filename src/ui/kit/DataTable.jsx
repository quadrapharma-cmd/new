import { useMemo, useState } from 'preact/hooks';
import { cx } from '../../lib/format.js';
import { S } from '../../lib/i18n.js';

/**
 * Scrollable table with sticky header, numeric columns and an optional totals row.
 * columns: [{ key, header, align:'start'|'num'|'center', render?(row, i), total?(rows)=>node, width?, sortable?, sortValue?(row), className?, mono? }]
 * The wrapper is the scroll container (overflow auto), so wide tables never widen the page.
 * Sticky header needs a bounded height: pass maxHeight (CSS length) or let `sticky` default it to 70vh.
 */
export function DataTable({ columns, rows, rowKey = (r, i) => r.id ?? i, caption, empty, totals = false, dense = false, sticky = true, maxHeight, onRowClick, rowClass, className, ariaLabel, initialSort }) {
  const [sort, setSort] = useState(initialSort || null); // { key, dir }
  const sorted = useMemo(() => {
    if (!sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    if (!col) return rows;
    const val = col.sortValue || ((r) => r[col.key]);
    const dir = sort.dir === 'desc' ? -1 : 1;
    return [...rows].sort((a, b) => {
      const x = val(a);
      const y = val(b);
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), 'ar')) * dir;
    });
  }, [rows, sort, columns]);

  const hasTotals = totals && columns.some((c) => c.total);
  const style = maxHeight ? { maxHeight } : sticky ? { maxHeight: '70vh' } : undefined;
  const cellClass = (c) => cx(c.align === 'num' && 'num', c.align === 'center' && 'center', c.mono && 'mono', c.className);

  return (
    <div className={cx('table-wrap', className)} style={style} tabIndex={0} role="region" aria-label={ariaLabel || caption || undefined}>
      <table className={cx('table', dense && 'table--dense')}>
        {caption ? <caption>{caption}</caption> : null}
        <thead>
          <tr>
            {columns.map((c) => {
              const active = sort && sort.key === c.key;
              return (
                <th key={c.key} scope="col" className={cx(c.align === 'num' && 'num', c.align === 'center' && 'center')} style={c.width ? { width: c.width } : undefined} aria-sort={active ? (sort.dir === 'desc' ? 'descending' : 'ascending') : undefined}>
                  {c.sortable ? (
                    <button type="button" className="th-sort" onClick={() => setSort(active && sort.dir === 'asc' ? { key: c.key, dir: 'desc' } : { key: c.key, dir: 'asc' })} title={active && sort.dir === 'asc' ? S.kit.table.sortDesc : S.kit.table.sortAsc}>
                      {c.header}
                      <span aria-hidden="true">{active ? (sort.dir === 'desc' ? '▼' : '▲') : ''}</span>
                    </button>
                  ) : (
                    c.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="table__empty">{empty || S.kit.table.empty}</td>
            </tr>
          ) : (
            sorted.map((r, i) => (
              <tr key={rowKey(r, i)} data-clickable={onRowClick ? 'true' : undefined} className={rowClass ? rowClass(r) : undefined} onClick={onRowClick ? () => onRowClick(r) : undefined}>
                {columns.map((c) => (
                  <td key={c.key} className={cellClass(c)}>
                    {c.render ? c.render(r, i) : r[c.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
        {hasTotals ? (
          <tfoot>
            <tr>
              {columns.map((c, i) => (
                <td key={c.key} className={cellClass(c)}>
                  {c.total ? c.total(sorted) : i === 0 ? S.common.total : null}
                </td>
              ))}
            </tr>
          </tfoot>
        ) : null}
      </table>
    </div>
  );
}
