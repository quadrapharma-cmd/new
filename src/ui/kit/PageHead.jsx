/** Page title row: <PageHead title="..." sub="..." actions={<Button/>} /> */
export function PageHead({ title, sub, actions }) {
  return (
    <div className="page-head">
      <div className="page-head__title">
        <h1>{title}</h1>
        {sub ? <p className="page-head__sub">{sub}</p> : null}
      </div>
      {actions ? <div className="page-head__actions">{actions}</div> : null}
    </div>
  );
}
