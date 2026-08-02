use pyo3::prelude::*;

/// A Python module implemented in Rust.
#[pymodule]
fn mitschreiber_core(_py: Python<'_>, _m: &Bound<'_, PyModule>) -> PyResult<()> {
    Ok(())
}
