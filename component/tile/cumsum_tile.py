from pathlib import Path
from datetime import datetime as dt

import ipyvuetify as v
from sepal_ui import sepalwidgets as sw
from sepal_ui.scripts import utils as su

from component import widget as cw
from component.message import cm
from component import scripts as cs
from component import parameter as cp


class CumSumTile(sw.Tile):
    def __init__(self):

        # create the different widgets
        # I will not use Io as the information doesn't need to be communicated to any other tile
        self.folder = cw.FolderSelect()
        self.out_dir = cw.OutDirSelect()
        self.tiles = cw.TilesSelect()
        self.bstraps = v.Slider(
            label=cm.widget.bstraps.label,
            v_model=1000,
            min=10,
            max=1000,
            thumb_label="always",
            class_="mt-5",
        )
        self.conf_thld = v.Slider(
            label=cm.widget.conf_thld.label,
            v_model=0.15,
            step=0.05,
            min=0,
            max=0.95,
            thumb_label="always",
            class_="mt-5",
        )
        self.period = cw.DateRangeSlider(label=cm.widget.period.label)

        # stack the advance parameters in a expandpanel
        advance_params = v.ExpansionPanels(
            class_="mb-5",
            popout=True,
            children=[
                v.ExpansionPanel(
                    children=[
                        v.ExpansionPanelHeader(children=[cm.widget.advance_params]),
                        v.ExpansionPanelContent(
                            children=[
                                v.Flex(xs12=True, children=[self.bstraps]),
                                v.Flex(xs12=True, children=[self.conf_thld]),
                            ]
                        ),
                    ]
                )
            ],
        )

        # create the tile
        super().__init__(
            "cumsum_tile",
            cm.cumsum.folder,  # the title is used to describe the first section
            inputs=[
                self.folder,
                self.out_dir,
                self.tiles,
                v.Html(tag="h2", children=[cm.cumsum.process]),
                advance_params,
                v.Html(tag="h2", children=[cm.cumsum.periods]),
                self.period,
            ],
            alert=cw.CustomAlert(),
            btn=sw.Btn(cm.cumsum.btn),
        )

        # add js behaviour
        self.folder.observe(self._on_folder_change, "v_model")
        self.btn.on_event("click", self._start_process)
        self.period.observe(self._check_periods, "v_model")

    @su.loading_button(debug=True)
    def _start_process(self, widget, event, data):
        """start the cumsum process"""

        # gather all the variables for conveniency
        folder = self.folder.v_model
        out_dir = self.out_dir.v_model
        tiles = self.tiles.v_model
        bstraps = self.bstraps.v_model
        area_thld = 0
        conf_thld = self.conf_thld.v_model
        period = self.period.v_model

        # check the inputs
        if not self.alert.check_input(folder, cm.widget.folder.no_folder):
            return
        if not self.alert.check_input(out_dir, cm.widget.out_dir.no_dir):
            return
        if not self.alert.check_input(tiles, cm.widget.tiles.no_tiles):
            return
        if not self.alert.check_input(period, cm.widget.period.no_dates):
            return
        if not self.alert.check_input(bstraps, cm.widget.bstraps.no_bstraps):
            return
        if not self.alert.check_input(conf_thld, cm.widget.conf_thld.no_conf_thld):
            return

        # run the cumsum process
        cs.run_cumsum(
            Path(folder),
            Path(out_dir),
            tiles,
            period,
            bstraps,
            area_thld,
            conf_thld,
            self.alert,
        )

        # display the end of computation message
        self.alert.add_live_msg(cm.cumsum.complete.format(out_dir), "success")

    def _on_folder_change(self, change):
        """
        Change the available tiles according to the selected folder
        Raise an error if the folder is not structured as a SEPAL time series (i.e. folder number for each tile)
        """

        # get the new selected folder
        folder = Path(change["new"])

        # reset the widgets
        self.out_dir.v_model = None
        self.tiles.reset()

        # check if it's a time series folder
        if not self.folder.is_valid_ts():

            # reset the non working inputs
            self.period.disable()
            self.tiles.reset()
            self.dates_0 = None

            # display a message to the end user
            self.alert.add_msg(cm.widget.folder.no_ts.format(folder), "warning")

            return self

        # set the basename
        self.out_dir.set_folder(folder)

        # set the items in the dropdown
        self.tiles.set_items(folder)

        # set the dates for the sliders
        # we consider that the dates are consistent through all the folders so we can use only the first one
        with (folder / "0" / "dates.csv").open() as f:
            dates = sorted(
                [
                    dt.strptime(l, "%Y-%m-%d")
                    for l in f.read().splitlines()
                    if l.rstrip()
                ]
            )

        self.period.set_dates(dates)

        self.alert.add_msg(cm.widget.folder.valid_ts.format(folder))

        return self

    def _check_periods(self, change):
        """check if the historical period have enough images"""

        # to avoid bug on disable
        if not self.period.dates:
            return self

        # get the dates from the folder
        folder = Path(self.folder.v_model)
        with (folder / "0" / "dates.csv").open() as f:
            dates = sorted(
                [
                    dt.strptime(l, "%Y-%m-%d")
                    for l in f.read().splitlines()
                    if l.rstrip()
                ]
            )

        # create datelist for selected period
        dates_filtered = [
            d
            for d in dates
            if d > self.period.v_model[0] and d < self.period.v_model[1]
        ]

        if len(dates_filtered) < cp.min_images:
            self.alert.add_msg(cm.widget.period.too_short, "warning")
        else:
            self.alert.reset()

        return self
