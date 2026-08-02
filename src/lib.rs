use pyo3::prelude::*;

use mitschreiber_sampler::{poll_state, start_session, stop_session};

/// The main `_mitschreiber` Python module.
#[pymodule]
fn _mitschreiber(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(start_session, m)?)?;
    m.add_function(wrap_pyfunction!(stop_session, m)?)?;
    m.add_function(wrap_pyfunction!(poll_state, m)?)?;
    Ok(())
}
