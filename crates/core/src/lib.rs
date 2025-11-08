use pyo3::prelude::*;

/// A Python module implemented in Rust.
#[pymodule]
fn hauski_core(_py: Python, _m: &PyModule) -> PyResult<()> {
    Ok(())
}
