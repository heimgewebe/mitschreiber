use pyo3::prelude::*;

use mitschreiber_sampler::{start_session, stop_session, poll_state};

/// The main `_mitschreiber` Python module.
#[pymodule]
fn _mitschreiber(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(start_session, m)?)?;
    m.add_function(wrap_pyfunction!(stop_session, m)?)?;
    m.add_function(wrap_pyfunction!(poll_state, m)?)?;
    Ok(())
}
