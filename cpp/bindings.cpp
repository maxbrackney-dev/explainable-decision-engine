#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "engine.h"

namespace py = pybind11;

PYBIND11_MODULE(decision_engine_core, m) {
    m.doc() = "Hybrid C++ decision engine core: deterministic labeling + OOD warnings";

    m.def(
        "label_from_threshold",
        &engine::label_from_threshold,
        py::arg("prob"),
        py::arg("threshold"),
        "Return 'high_risk' if prob >= threshold else 'low_risk'."
    );

    m.def(
        "ood_warnings",
        &engine::ood_warnings,
        py::arg("payload"),
        py::arg("means"),
        py::arg("stds"),
        py::arg("z_threshold"),
        "Return list of OOD warnings based on z-score threshold."
    );
}