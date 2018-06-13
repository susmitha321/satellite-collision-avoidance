# Module simulator provides simulator of space environment
# and learning proccess of the agent.

import logging
import time

import numpy as np

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from mpl_toolkits.mplot3d import Axes3D

import pykep as pk
from pykep.orbit_plots import plot_planet


logging.basicConfig(filename="simulator.log", level=logging.DEBUG,
                    filemode='w', format='%(name)s:%(levelname)s\n%(message)s\n')

PAUSE_TIME = 0.0001  # sc
PAUSE_ACTION_TIME = 2  # sc
ARROW_LENGTH = 3e6  # meters
EARTH_RADIUS = 6.3781e6  # meters


def draw_sphere(axis, centre, radius, wireframe_params={}):
    """
    Draws a wireframe sphere.
    Args:
       axis (matplotlib.axes._subplots.Axes3DSubplot): axis to plot on
       centre (list-like): sphere centre. Must support [] operator
       radius (float): sphere radius
       wireframe_params (dict): arguments to pass to plot_wireframe
    Returns:
       mpl_toolkits.mplot3d.art3d.Line3DCollection
    """
    u, v = np.mgrid[0:2 * np.pi:20j, 0:np.pi:10j]
    x = radius * np.cos(u) * np.sin(v) + centre[0]
    y = radius * np.sin(u) * np.sin(v) + centre[1]
    z = radius * np.cos(v) + centre[2]
    return axis.plot_wireframe(x, y, z, **wireframe_params)


def draw_action(axis, pos, dV):
    """ Draws action.
    Args:
        axis (matplotlib.axes._subplots.Axes3DSubplot): axis to plot on
        pos ([x, y, z]): position of protecred object
        dV ([dVx, dVy, dVz]): action
    """
    x, y, z = pos
    dVx, dVy, dVz = dV
    return axis.quiver(x, y, z, x + dVx, y + dVy, z + dVz, length=ARROW_LENGTH, normalize=True)


def strf_position(satellite, epoch):
    """ Print SpaceObject position at epoch. """
    pos, vel = satellite.position(epoch)
    return "{} position: x - {:0.5f}, y - {:0.5f}, z - {:0.5f}.\
      \n{} velocity: Vx - {:0.5f}, Vy - {:0.5f}, Vz - {:0.5f}\
      ".format(satellite.get_name(), pos[0], pos[1], pos[2],
               satellite.get_name(), vel[0], vel[1], vel[2])


class Visualizer:
    """ Visualizer allows to plot satellite movement simulation
        in real time.
    """

    def __init__(self, curr_time, total_collision_probability, fuel_cons, traj_dev, reward_components, reward):
        self.fig = plt.figure(figsize=[14, 12])
        self.gs = gridspec.GridSpec(15, 2)
        self.subplot_3d = self.fig.add_subplot(self.gs[:, 0], projection='3d')
        self.subplot_3d.set_aspect("equal")
        self.subplot_p = self.fig.add_subplot(self.gs[:3, 1])
        self.subplot_f = self.fig.add_subplot(self.gs[4:7, 1])
        self.subplot_d = self.fig.add_subplot(self.gs[8:11, 1])
        self.subplot_r = self.fig.add_subplot(self.gs[12:, 1])
        # initialize data for plots
        self.time_arr = [0]
        self.prob_arr = [total_collision_probability]
        self.fuel_cons_arr = [fuel_cons]
        self.traj_dev_arr = [traj_dev]
        self.reward_arr = [reward]
        self.reward_components = reward_components

    def run(self):
        plt.ion()

    def update_data(self, curr_time, prob, fuel_cons, traj_dev, reward_components, reward):
        self.time_arr.append(curr_time)
        self.prob_arr.append(prob)
        self.fuel_cons_arr.append(fuel_cons)
        self.traj_dev_arr.append(traj_dev)
        self.reward_arr.append(reward)
        self.reward_components = reward_components

    def plot_planet(self, satellite, t, size, color):
        """ Plot a pykep.planet object. """
        plot_planet(satellite, ax=self.subplot_3d,
                    t0=t, s=size, legend=True, color=color)

    def plot_earth(self):
        """ Add earth to the plot and legend. """
        draw_sphere(self.subplot_3d, (0, 0, 0), EARTH_RADIUS, {
            "color": "b", "lw": 0.5, "alpha": 0.2})
        plt.legend()

    def pause(self, pause_time):
        """ Pause the frame to watch it. """
        plt.legend()
        plt.pause(pause_time)

    def clear(self):
        """ Clear axis for next frame. """
        self.subplot_3d.cla()
        self.subplot_p.cla()
        self.subplot_f.cla()
        self.subplot_d.cla()
        self.subplot_r.cla()

    def plot_iteration(self, epoch, last_update):
        s = '  Epoch: {}\nUpdate: {}'.format(epoch, last_update)
        s += '\n\nColl Prob: {:.7}     Fuel Cons: {:.5}     Traj Dev coef: {:.5}'.format(
            self.prob_arr[-1], self.fuel_cons_arr[-1], self.traj_dev_arr[-1])
        s += '\n\nReward components:\nColl Prob R: {:.5}     Fuel Cons R: {:.5}     Traj Dev coef R: {:.5}\
            \nTotal Reward: {:.5}'.format(
            self.reward_components[0], self.reward_components[1], self.reward_components[2], self.reward_arr[-1])
        self.subplot_3d.text2D(-0.3, 1.05, s,
                               transform=self.subplot_3d.transAxes)

    def plot_prob_fuel_reward(self):
        self.make_step_on_graph(self.subplot_p, self.time_arr, self.prob_arr,
                                title='Total collision probability', ylabel='prob')
        self.make_step_on_graph(self.subplot_f, self.time_arr, self.fuel_cons_arr,
                                title='Total fuel consumption', ylabel='fuel (dV)')
        self.make_step_on_graph(self.subplot_d, self.time_arr, self.traj_dev_arr,
                                title='Trajectory deviation coefficient', ylabel='traj dev coef')
        self.make_step_on_graph(self.subplot_r, self.time_arr, self.reward_arr,
                                title='Total reward', ylabel='reward', xlabel='time (mjd2000)')

    def make_step_on_graph(self, ax, time, data, title, ylabel, xlabel=None):
        ax.step(time, data)
        ax.set_title(title)
        ax.grid(True)
        ax.set_ylabel(ylabel)
        if xlabel is not None:
            ax.set_xlabel(xlabel)

    def plot_action(self, pos, action):
        draw_action(self.subplot_3d, pos, action)

    def save_graphics(self):
        fig = plt.figure(figsize=[7, 12])
        gs = gridspec.GridSpec(15, 1)
        subplot_p = fig.add_subplot(gs[:3, 0])
        subplot_f = fig.add_subplot(gs[4:7, 0])
        subplot_d = fig.add_subplot(gs[8:11, 0])
        subplot_r = fig.add_subplot(gs[12:, 0])

        self.make_step_on_graph(subplot_p, self.time_arr, self.prob_arr,
                                title='Total collision probability', ylabel='prob')
        self.make_step_on_graph(subplot_f, self.time_arr, self.fuel_cons_arr,
                                title='Total fuel consumption', ylabel='fuel (dV)')
        self.make_step_on_graph(subplot_d, self.time_arr, self.traj_dev_arr,
                                title='Trajectory deviation coefficient', ylabel='traj dev coef')
        self.make_step_on_graph(subplot_r, self.time_arr, self.reward_arr,
                                title='Total reward', ylabel='reward', xlabel='time since simulation starts (mjd2000)')

        fig.savefig("simulation_graphics.png")


class Simulator:
    """ Simulator allows to start the simulation of provided environment,
        and starts agent-environment collaboration.
    """

    def __init__(self, agent, environment, step=0.001, n_steps_to_update=None, each_step_propagation=False):
        """
        Args:
            agent (api.Agent, agent, to do actions in environment.
            environment (api.Environment): the initial space environment.
            step (float): time step in simulation.
            n_steps_to_update (int): number of steps to updating the
                collision probability, trajectory_deviation and reward
                (if update_step == None, updated if necessary).
            print_out (bool): print out some parameters and results (reward and probability).

        TODO:
            check all models using simulator.
        """

        self.agent = agent
        self.env = environment
        self.start_time = self.env.init_params["start_time"]
        self.end_time = self.env.init_params["end_time"]
        self.curr_time = self.start_time

        self.step = step
        self.n_steps_to_update = n_steps_to_update

        self.vis = None
        self.logger = None

    def run(self, visualize=False, print_out=False, log=True):
        """
        Args:
            visualize (bool): whether show the simulation or not.
            print_out (bool): whether show the print out or not.
            log (bool): whether log the simulation or not.

        Returns:
            reward (float): reward of session.

        """
        action = np.zeros(4)
        iteration = 0
        if visualize:
            self.vis = Visualizer(self.curr_time.mjd2000, self.env.total_collision_probability,
                                  self.env.get_fuel_consumption(), self.env.get_trajectory_deviation(),
                                  self.env.reward_components, self.env.reward)
            self.vis.run()

        if print_out:
            self.print_start()
            simulation_start_time = time.time()

        if log:
            self.logger = logging.getLogger('simulator.Simulator')

        while True:
            self.env.propagate_forward(
                self.curr_time.mjd2000, self.n_steps_to_update)

            print("curr:", self.curr_time.mjd2000,
                  "    next:", self.env.get_next_action().mjd2000,
                  "    end:", self.end_time.mjd2000)

            if self.curr_time.mjd2000 >= self.env.get_next_action().mjd2000:
                s = self.env.get_state()
                action = self.agent.get_action(s)
                err = self.env.act(action)
                if log:
                    self.env.update_all_reward_components()
                    r = self.env.get_reward()
                    if err:
                        self.log_bad_action(err, action)

                    self.log_reward_action(iteration, r, action)

            if log:
                self.log_iteration(iteration)
                self.log_protected_position()
                self.log_debris_positions()

            if visualize:
                self.plot_protected()
                self.plot_debris()
                self.vis.plot_earth()
                if iteration % self.n_steps_to_update == 0:
                    self.update_vis_data()
                if np.not_equal(action[:3], np.zeros(3)).all():
                    self.vis.plot_action(self.env.protected.position(
                        self.curr_time)[0], action[:3])
                    self.vis.pause(PAUSE_ACTION_TIME)
                    # set action to zero after it is done
                    action = np.zeros(4)
                self.vis.plot_prob_fuel_reward()
                self.vis.pause(PAUSE_TIME)
                self.vis.clear()

                # self.env.reward and self.env.total_collision_probability -
                # without update.
                self.vis.plot_iteration(
                    self.curr_time, self.env.last_r_p_update)

            next_action_time = self.env.get_next_action().mjd2000

            if self.curr_time.mjd2000 >= self.end_time.mjd2000:
                break

            if np.isnan(next_action_time) or next_action_time > self.end_time.mjd2000:
                self.curr_time = self.end_time
            else:
                self.curr_time = pk.epoch(
                    next_action_time, "mjd2000")

            iteration += 1

        self.env.update_all_reward_components()
        if log:
            self.log_protected_position()

        if visualize:
            self.update_vis_data()
            self.vis.save_graphics()
        if print_out:
            self.print_end(simulation_start_time)

        return self.env.get_reward()

    def log_protected_position(self):
        self.logger.info(strf_position(self.env.protected, self.curr_time))

    def log_debris_positions(self):
        for obj in self.env.debris:
            self.logger.info(strf_position(obj, self.curr_time))

    def log_iteration(self, iteration):
        self.logger.debug("Iter #{} \tEpoch: {} \tCollision Probability: {}".format(
            iteration,  self.curr_time, self.env.total_collision_probability))

    def log_reward_action(self, iteration, reward, action):
        self.logger.info("Iter: {} \tReward: {} \taction: (dVx:{}, dVy: {}, dVz: {}, time_to_request: {})".format(
            iteration, reward, *action))

    def log_bad_action(self, message, action):
        self.logger.warning(
            "Unable to make action (dVx:{}, dVy:{}, dVz:{}): {}".format(action[0], action[1], action[2], message))

    def plot_protected(self):
        """ Plot Protected SpaceObject. """
        self.vis.plot_planet(self.env.protected.satellite,
                             t=self.curr_time, size=100, color="black")

    def plot_debris(self):
        """ Plot space debris. """
        cmap = plt.get_cmap('gist_rainbow')
        n_items = len(self.env.debris)
        colors = [cmap(i) for i in np.linspace(0, 1, n_items)]
        for i in range(n_items):
            self.vis.plot_planet(
                self.env.debris[i].satellite, t=self.curr_time,
                size=25, color=colors[i])

    def update_vis_data(self):
        # TODO - better time difference
        self.vis.update_data(
            self.curr_time.mjd2000 - self.start_time.mjd2000,
            self.env.get_total_collision_probability(),
            self.env.get_fuel_consumption(), self.env.get_trajectory_deviation(),
            self.env.get_reward_components(), self.env.get_reward())

    def print_start(self):
        print("Simulation started.\n\nStart time: {} \t End time: {} \t Simulation step:{}\n".format(
            self.start_time.mjd2000, self.end_time.mjd2000, self.step))
        print("Protected SpaceObject:\n{}".format(
            self.env.protected.satellite))
        print("Debris objects:\n")
        for spaceObject in self.env.debris:
            print(spaceObject.satellite)

    def print_end(self, simulation_start_time):
        reward_components = self.env.get_reward_components()
        s = "Simulation ended in {:.5} sec.\n\nCollision probability: {:.5}\nFuel consumption: {:.5}\
            \nTrajectory deviation coefficient: {:.5}".format(
            time.time() - simulation_start_time,
            self.env.get_total_collision_probability(), self.env.get_fuel_consumption(),
            self.env.get_trajectory_deviation())
        s += '\n\nReward components:\nColl Prob R: {:.5}     Fuel Cons R: {:.5}     Traj Dev coef R: {:.5}\
            \nTotal Reward: {:.5}'.format(
            reward_components[0], reward_components[1], reward_components[2], self.env.get_reward())
        print(s)
